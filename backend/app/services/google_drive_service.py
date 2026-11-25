import base64
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from uuid import uuid4

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.config import settings

logger = logging.getLogger("app.services.google_drive_service")

DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
DRIVE_ABOUT_URL = "https://www.googleapis.com/drive/v3/about"
DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"
GOOGLE_OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"

MIME_TYPES = {
    "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "PDF": "application/pdf",
    "ZIP": "application/zip",
}


def sanitize_drive_name(name: str, fallback: str = "Folder") -> str:
    """Sanitizes a folder or file name for Google Drive paths."""
    cleaned = re.sub(r"[\\/]+", "-", (name or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or fallback


def _escape_drive_query(value: str) -> str:
    """Escapes backslashes and single quotes for Google Drive q parameter."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


class GoogleDriveService:
    """Async Google Drive API v3 client supporting OAuth 2.0 (personal My Drive)
    and Service Account JWT (Google Workspace Shared Drive).
    """

    def __init__(self) -> None:
        self._cached_token: Optional[str] = None
        self._cached_auth_mode: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._connected_email: Optional[str] = None

    def _invalidate_cache(self) -> None:
        self._cached_token = None
        self._cached_auth_mode = None
        self._token_expires_at = 0.0
        self._connected_email = None

    def _load_service_account(self) -> Dict[str, Any]:
        cred_path = settings.get_drive_credentials_path()
        if not cred_path.exists():
            raise FileNotFoundError(
                f"Berkas kredensial Service Account tidak ditemukan di: {cred_path}"
            )
        return json.loads(cred_path.read_text(encoding="utf-8"))

    def _load_oauth_client_config(self) -> Dict[str, str]:
        client_path = settings.get_drive_oauth_client_path()
        if not client_path.exists():
            raise FileNotFoundError(
                f"Berkas OAuth Client JSON tidak ditemukan di: {client_path}. "
                "Unduh OAuth 2.0 Client ID JSON dari Google Cloud Console dan simpan sebagai "
                "backend/credentials/gdrive-oauth-client.json."
            )
        raw = json.loads(client_path.read_text(encoding="utf-8"))
        cfg = raw.get("web") or raw.get("installed") or raw
        client_id = cfg.get("client_id")
        client_secret = cfg.get("client_secret")
        if not client_id or not client_secret:
            raise ValueError(
                "Format gdrive-oauth-client.json tidak valid (client_id / client_secret tidak ditemukan)."
            )
        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": cfg.get("auth_uri") or GOOGLE_OAUTH_AUTH_URL,
            "token_uri": cfg.get("token_uri") or GOOGLE_OAUTH_TOKEN_URL,
        }

    def _load_oauth_token_data(self) -> Dict[str, Any]:
        token_path = settings.get_drive_oauth_token_path()
        if not token_path.exists():
            raise FileNotFoundError(
                f"Token OAuth Google Drive belum tersedia di: {token_path}"
            )
        data = json.loads(token_path.read_text(encoding="utf-8"))
        if (not data.get("client_id") or not data.get("client_secret")) and settings.get_drive_oauth_client_path().exists():
            client_cfg = self._load_oauth_client_config()
            data.setdefault("client_id", client_cfg["client_id"])
            data.setdefault("client_secret", client_cfg["client_secret"])
            data.setdefault("token_uri", client_cfg["token_uri"])
        return data

    def get_active_auth_mode(self) -> str:
        if settings.is_drive_oauth_configured():
            return "oauth2"
        if settings.get_drive_credentials_path().exists():
            return "service_account"
        return "none"

    def get_oauth_authorization_url(
        self,
        redirect_uri: Optional[str] = None,
        state: Optional[str] = None,
    ) -> str:
        """Builds the Google OAuth 2.0 consent URL for connecting a user's Google Drive."""
        cfg = self._load_oauth_client_config()
        effective_redirect = redirect_uri or settings.GOOGLE_DRIVE_OAUTH_REDIRECT_URI
        params = {
            "client_id": cfg["client_id"],
            "redirect_uri": effective_redirect,
            "response_type": "code",
            "scope": DRIVE_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
        }
        if state:
            params["state"] = state
        return f"{cfg['auth_uri']}?{urlencode(params)}"

    async def exchange_oauth_code(
        self,
        code: str,
        redirect_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Exchanges an OAuth authorization code for tokens and persists refresh_token."""
        cfg = self._load_oauth_client_config()
        effective_redirect = redirect_uri or settings.GOOGLE_DRIVE_OAUTH_REDIRECT_URI

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                cfg["token_uri"],
                data={
                    "code": code,
                    "client_id": cfg["client_id"],
                    "client_secret": cfg["client_secret"],
                    "redirect_uri": effective_redirect,
                    "grant_type": "authorization_code",
                },
            )

        if resp.status_code != 200:
            raise RuntimeError(
                f"Gagal menukar kode OAuth Google Drive ({resp.status_code}): {resp.text}"
            )

        token_payload = resp.json()
        access_token = token_payload["access_token"]
        refresh_token = token_payload.get("refresh_token")

        # Preserve existing refresh_token if Google omitted it on re-consent
        token_path = settings.get_drive_oauth_token_path()
        if not refresh_token and token_path.exists():
            try:
                old = json.loads(token_path.read_text(encoding="utf-8"))
                refresh_token = old.get("refresh_token")
            except Exception:
                pass

        if not refresh_token:
            raise RuntimeError(
                "Google tidak mengembalikan refresh_token. Silakan cabut akses aplikasi di "
                "https://myaccount.google.com/permissions lalu hubungkan ulang."
            )

        # Fetch connected user email
        connected_email = None
        async with httpx.AsyncClient(timeout=20.0) as client:
            about_resp = await client.get(
                DRIVE_ABOUT_URL,
                params={"fields": "user,storageQuota"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if about_resp.status_code == 200:
                connected_email = (about_resp.json().get("user") or {}).get("emailAddress")

        saved_data = {
            "type": "authorized_user",
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "refresh_token": refresh_token,
            "token_uri": cfg["token_uri"],
            "connected_email": connected_email,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(json.dumps(saved_data, indent=2), encoding="utf-8")

        self._cached_token = access_token
        self._cached_auth_mode = "oauth2"
        self._token_expires_at = time.time() + int(token_payload.get("expires_in", 3600))
        self._connected_email = connected_email

        return {
            "connected": True,
            "connected_email": connected_email,
            "token_path": str(token_path),
        }

    def disconnect_oauth(self) -> bool:
        """Removes the stored OAuth token JSON and resets cached credentials."""
        token_path = settings.get_drive_oauth_token_path()
        existed = token_path.exists()
        if existed:
            token_path.unlink()
        self._invalidate_cache()
        return existed

    async def get_access_token(self, force_refresh: bool = False) -> str:
        """Obtains and caches a Google OAuth2 bearer token using OAuth2 refresh_token (preferred)
        or Service Account JWT fallback.
        """
        mode = self.get_active_auth_mode()
        if mode == "none":
            raise FileNotFoundError(
                "Kredensial Google Drive belum tersedia (gdrive-oauth-token.json maupun gdrive-service-account.json)."
            )

        now = time.time()
        if (
            not force_refresh
            and self._cached_token
            and self._cached_auth_mode == mode
            and now < (self._token_expires_at - 300)
        ):
            return self._cached_token

        if mode == "oauth2":
            oauth_data = self._load_oauth_token_data()
            refresh_token = oauth_data.get("refresh_token")
            client_id = oauth_data.get("client_id")
            client_secret = oauth_data.get("client_secret")
            token_uri = oauth_data.get("token_uri") or GOOGLE_OAUTH_TOKEN_URL
            self._connected_email = oauth_data.get("connected_email")

            if not (refresh_token and client_id and client_secret):
                raise RuntimeError(
                    "Data token OAuth2 tidak lengkap. Silakan hubungkan ulang akun Google Drive."
                )

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    token_uri,
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Gagal memperbarui token OAuth2 Google Drive ({resp.status_code}): {resp.text}"
                )

            token_resp = resp.json()
            self._cached_token = token_resp["access_token"]
            self._cached_auth_mode = "oauth2"
            self._token_expires_at = now + int(token_resp.get("expires_in", 3600))
            return self._cached_token

        # Service Account JWT flow
        sa = self._load_service_account()
        self._connected_email = sa.get("client_email")
        now_int = int(now)
        header = {"alg": "RS256", "typ": "JWT"}
        payload = {
            "iss": sa["client_email"],
            "scope": DRIVE_SCOPE,
            "aud": sa["token_uri"],
            "exp": now_int + 3600,
            "iat": now_int,
        }
        signing_input = (
            f"{_b64url(json.dumps(header).encode('utf-8'))}."
            f"{_b64url(json.dumps(payload).encode('utf-8'))}"
        ).encode("utf-8")

        private_key = serialization.load_pem_private_key(
            sa["private_key"].encode("utf-8"),
            password=None,
        )
        signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        jwt_assertion = f"{signing_input.decode('utf-8')}.{_b64url(signature)}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                sa["token_uri"],
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": jwt_assertion,
                },
            )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Gagal autentikasi token Service Account Google Drive ({resp.status_code}): {resp.text}"
            )

        token_data = resp.json()
        self._cached_token = token_data["access_token"]
        self._cached_auth_mode = "service_account"
        self._token_expires_at = now + int(token_data.get("expires_in", 3600))
        return self._cached_token

    async def _auth_headers(self) -> Dict[str, str]:
        token = await self.get_access_token()
        return {"Authorization": f"Bearer {token}"}

    async def _ensure_folder(
        self,
        client: httpx.AsyncClient,
        headers: Dict[str, str],
        parent_id: str,
        folder_name: str,
    ) -> Dict[str, str]:
        """Finds an existing folder by exact name under parent_id or creates it."""
        escaped_name = _escape_drive_query(folder_name)
        query = (
            f"'{parent_id}' in parents and name = '{escaped_name}' "
            f"and mimeType = '{DRIVE_FOLDER_MIME}' and trashed = false"
        )
        resp = await client.get(
            DRIVE_FILES_URL,
            params={
                "q": query,
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
                "fields": "files(id,name,webViewLink)",
                "pageSize": 5,
            },
            headers=headers,
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Gagal mencari folder '{folder_name}' di Google Drive ({resp.status_code}): {resp.text}"
            )

        files = resp.json().get("files", [])
        if files:
            fld = files[0]
            return {
                "id": fld["id"],
                "name": fld.get("name", folder_name),
                "webViewLink": fld.get("webViewLink")
                or f"https://drive.google.com/drive/folders/{fld['id']}",
            }

        create_resp = await client.post(
            DRIVE_FILES_URL,
            params={
                "supportsAllDrives": "true",
                "fields": "id,name,webViewLink",
            },
            headers={**headers, "Content-Type": "application/json"},
            json={
                "name": folder_name,
                "mimeType": DRIVE_FOLDER_MIME,
                "parents": [parent_id],
            },
        )
        if create_resp.status_code not in (200, 201):
            raise RuntimeError(
                f"Gagal membuat folder '{folder_name}' di Google Drive ({create_resp.status_code}): {create_resp.text}"
            )

        created = create_resp.json()
        return {
            "id": created["id"],
            "name": created.get("name", folder_name),
            "webViewLink": created.get("webViewLink")
            or f"https://drive.google.com/drive/folders/{created['id']}",
        }

    async def ensure_hierarchy(
        self,
        school_name: str,
        fiscal_year: int,
        quarter: int,
        package_number: str = "Paket",
    ) -> Dict[str, str]:
        """Ensures 4-level folder hierarchy under root (5 levels total with documents):
        Lv1 (Sekolah) -> Lv2 (Year) -> Lv3 (Triwulan) -> Lv4 (Kode Pengadaan).
        """
        root_id = settings.get_effective_drive_root_folder_id()
        if not root_id:
            raise RuntimeError(
                "GOOGLE_DRIVE_ROOT_FOLDER_ID belum dikonfigurasi dan file gdrive-folder-id.txt kosong/tidak ada."
            )

        lv1_name = sanitize_drive_name(school_name, fallback="Sekolah")
        lv2_name = sanitize_drive_name(str(fiscal_year), fallback="2026")
        lv3_name = f"Triwulan {quarter}"
        lv4_name = sanitize_drive_name(package_number, fallback="Paket")

        headers = await self._auth_headers()
        async with httpx.AsyncClient(timeout=60.0) as client:
            lv1 = await self._ensure_folder(client, headers, root_id, lv1_name)
            lv2 = await self._ensure_folder(client, headers, lv1["id"], lv2_name)
            lv3 = await self._ensure_folder(client, headers, lv2["id"], lv3_name)
            lv4 = await self._ensure_folder(client, headers, lv3["id"], lv4_name)

        return {
            "folder_id": lv4["id"],
            "folder_url": lv4["webViewLink"],
            "display_path": f"{lv1_name} / {lv2_name} / {lv3_name} / {lv4_name}",
            "lv1_folder_id": lv1["id"],
            "lv2_folder_id": lv2["id"],
            "lv3_folder_id": lv3["id"],
        }

    @staticmethod
    def resolve_canonical_filename(doc_code: Optional[str], fmt: str, original_filename: str) -> str:
        """Ensures deterministic filenames across revisions so newer revisions overwrite prior ones."""
        if (doc_code or "").upper() == "ZIP" or (fmt or "").upper() == "ZIP":
            return "00_PAKET_ARSIP_LENGKAP.zip"
        return original_filename

    async def _find_existing_files(
        self,
        client: httpx.AsyncClient,
        headers: Dict[str, str],
        folder_id: str,
        filename: str,
    ) -> List[Dict[str, Any]]:
        escaped = _escape_drive_query(filename)
        query = (
            f"'{folder_id}' in parents and name = '{escaped}' "
            f"and mimeType != '{DRIVE_FOLDER_MIME}' and trashed = false"
        )
        resp = await client.get(
            DRIVE_FILES_URL,
            params={
                "q": query,
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
                "fields": "files(id,name,webViewLink,size)",
                "orderBy": "modifiedTime desc",
            },
            headers=headers,
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Gagal memeriksa berkas '{filename}' di Google Drive ({resp.status_code}): {resp.text}"
            )
        return resp.json().get("files", [])

    async def _delete_or_remove_file(
        self,
        client: httpx.AsyncClient,
        headers: Dict[str, str],
        file_id: str,
        parent_folder_id: str,
    ) -> None:
        """Deletes, trashes (for Shared Drive Content Manager), or detaches a stale/duplicate file."""
        resp = await client.delete(
            f"{DRIVE_FILES_URL}/{file_id}",
            params={"supportsAllDrives": "true"},
            headers=headers,
        )
        if resp.status_code in (200, 204):
            return

        # Shared Drive Content Managers have canTrash=True but canDelete=False (DELETE returns 403/404)
        trash_resp = await client.patch(
            f"{DRIVE_FILES_URL}/{file_id}",
            params={"supportsAllDrives": "true"},
            headers={**headers, "Content-Type": "application/json"},
            json={"trashed": True},
        )
        if trash_resp.status_code in (200, 204):
            return

        # If caller owns the parent folder in My Drive (e.g. replacing a 0-byte SA file via OAuth),
        # remove the old file from the parent folder so there is no duplicate.
        detach_resp = await client.patch(
            f"{DRIVE_FILES_URL}/{file_id}",
            params={
                "removeParents": parent_folder_id,
                "supportsAllDrives": "true",
            },
            headers={**headers, "Content-Type": "application/json"},
            json={},
        )
        if detach_resp.status_code not in (200, 204, 404):
            logger.warning(
                f"Gagal menghapus/melepas duplikat berkas Drive {file_id}: "
                f"del={resp.status_code}, trash={trash_resp.status_code}, detach={detach_resp.status_code}"
            )

    async def upload_or_overwrite_file(
        self,
        local_path: Path,
        folder_id: str,
        target_filename: str,
        fmt: str,
        package_number: str = "",
        revision_number: int = 1,
        sha256_hash: str = "",
        file_size: int = 0,
    ) -> Dict[str, Any]:
        """Uploads full binary file content into folder_id, overwriting any existing file
        (including replacing any stale 0-byte files) with the same canonical name.
        """
        if not local_path.exists():
            raise FileNotFoundError(f"Berkas lokal tidak ditemukan untuk diunggah: {local_path}")

        file_bytes = local_path.read_bytes()
        if len(file_bytes) == 0:
            raise ValueError(f"Berkas lokal '{local_path.name}' berukuran 0 byte dan tidak dapat diunggah.")

        mime_type = MIME_TYPES.get((fmt or "").upper(), "application/octet-stream")
        headers = await self._auth_headers()
        description = (
            f"PCI Procurement SPJ | Paket: {package_number} | Rev-{revision_number} "
            f"| SHA256: {sha256_hash} | Size: {len(file_bytes)}B"
        )

        async with httpx.AsyncClient(timeout=180.0) as client:
            existing_files = await self._find_existing_files(client, headers, folder_id, target_filename)
            was_overwritten = len(existing_files) > 0
            existing_file_id: Optional[str] = None

            if existing_files:
                primary = existing_files[0]
                primary_size = int(primary.get("size") or 0)
                if primary_size == 0:
                    # Replace stale 0-byte placeholder cleanly with a fresh binary upload
                    await self._delete_or_remove_file(client, headers, primary["id"], folder_id)
                else:
                    existing_file_id = primary["id"]

                for dup in existing_files[1:]:
                    await self._delete_or_remove_file(client, headers, dup["id"], folder_id)

            def _build_multipart(include_parents: bool) -> tuple[bytes, str]:
                meta: Dict[str, Any] = {
                    "name": target_filename,
                    "mimeType": mime_type,
                    "description": description,
                }
                if include_parents:
                    meta["parents"] = [folder_id]
                boundary = f"pci_drive_boundary_{uuid4().hex}"
                meta_bytes = json.dumps(meta, ensure_ascii=False).encode("utf-8")
                body = (
                    f"--{boundary}\r\n"
                    f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
                ).encode("utf-8") + meta_bytes + (
                    f"\r\n--{boundary}\r\n"
                    f"Content-Type: {mime_type}\r\n\r\n"
                ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
                return body, boundary

            params = {
                "uploadType": "multipart",
                "supportsAllDrives": "true",
                "fields": "id,name,webViewLink,size",
            }

            if existing_file_id:
                multipart_body, boundary = _build_multipart(include_parents=False)
                resp = await client.patch(
                    f"{DRIVE_UPLOAD_URL}/{existing_file_id}",
                    params=params,
                    headers={
                        **headers,
                        "Content-Type": f"multipart/related; boundary={boundary}",
                    },
                    content=multipart_body,
                )
                # If existing file was owned by another account (e.g. SA vs OAuth user), remove & re-create
                if resp.status_code in (403, 404) and "storageQuotaExceeded" not in resp.text:
                    await self._delete_or_remove_file(client, headers, existing_file_id, folder_id)
                    existing_file_id = None

            if not existing_file_id:
                multipart_body, boundary = _build_multipart(include_parents=True)
                resp = await client.post(
                    DRIVE_UPLOAD_URL,
                    params=params,
                    headers={
                        **headers,
                        "Content-Type": f"multipart/related; boundary={boundary}",
                    },
                    content=multipart_body,
                )

            if resp.status_code == 403 and "storageQuotaExceeded" in resp.text:
                raise RuntimeError(
                    "Google Drive menolak unggahan (403 storageQuotaExceeded): Service Account memiliki kuota 0 byte "
                    "pada My Drive pribadi. Hubungkan akun Google Anda via OAuth 2.0 "
                    "(backend/credentials/gdrive-oauth-client.json) atau gunakan Google Workspace Shared Drive."
                )

            if resp.status_code not in (200, 201):
                raise RuntimeError(
                    f"Gagal mengunggah '{target_filename}' ke Google Drive ({resp.status_code}): {resp.text}"
                )

            data = resp.json()
            uploaded_size = int(data.get("size") or 0)
            if uploaded_size == 0:
                raise RuntimeError(
                    f"Berkas '{target_filename}' terunggah dengan ukuran 0 byte di Google Drive."
                )

            file_id = data["id"]
            return {
                "id": file_id,
                "name": data.get("name", target_filename),
                "webViewLink": data.get("webViewLink")
                or f"https://drive.google.com/file/d/{file_id}/view",
                "size": uploaded_size,
                "overwritten": was_overwritten,
            }

    async def check_health(self) -> Dict[str, Any]:
        """Verifies Drive credentials, auth mode, storage quota, and root folder access."""
        mode = "live" if settings.is_drive_live_configured() else "mock"
        auth_mode = self.get_active_auth_mode()
        sa_present = settings.get_drive_credentials_path().exists()
        oauth_client_present = settings.get_drive_oauth_client_path().exists()
        oauth_connected = settings.is_drive_oauth_configured()
        root_folder_id = settings.get_effective_drive_root_folder_id()

        result: Dict[str, Any] = {
            "enabled": settings.DRIVE_SYNC_ENABLED,
            "mode": mode,
            "auth_mode": auth_mode,
            "connected": False,
            "can_upload_binary": False,
            "credentials_present": sa_present or oauth_connected,
            "service_account_present": sa_present,
            "oauth_client_configured": oauth_client_present,
            "oauth_connected": oauth_connected,
            "root_folder_id": root_folder_id,
            "root_folder_name": None,
            "root_folder_url": None,
            "is_shared_drive": False,
            "connected_email": None,
            "service_account_email": None,
            "storage_quota": None,
            "error": None,
        }

        if sa_present:
            try:
                result["service_account_email"] = self._load_service_account().get("client_email")
            except Exception:
                pass

        if auth_mode == "none":
            result["error"] = "Belum ada kredensial Google Drive (OAuth 2.0 maupun Service Account)."
            return result

        if not root_folder_id:
            result["error"] = "Root Folder ID Google Drive tidak dikonfigurasi."
            return result

        try:
            headers = await self._auth_headers()
            async with httpx.AsyncClient(timeout=20.0) as client:
                fld_resp = await client.get(
                    f"{DRIVE_FILES_URL}/{root_folder_id}",
                    params={
                        "supportsAllDrives": "true",
                        "fields": "id,name,mimeType,webViewLink,driveId,capabilities(canAddChildren,canEdit)",
                    },
                    headers=headers,
                )
                about_resp = await client.get(
                    DRIVE_ABOUT_URL,
                    params={"fields": "user,storageQuota"},
                    headers=headers,
                )

            if fld_resp.status_code != 200:
                result["error"] = (
                    f"Folder root tidak dapat diakses ({fld_resp.status_code}): {fld_resp.text}"
                )
                return result

            fld = fld_resp.json()
            is_shared_drive = bool(fld.get("driveId"))
            result["root_folder_name"] = fld.get("name")
            result["root_folder_url"] = (
                fld.get("webViewLink") or f"https://drive.google.com/drive/folders/{root_folder_id}"
            )
            result["is_shared_drive"] = is_shared_drive
            result["connected"] = True

            quota = None
            if about_resp.status_code == 200:
                about_data = about_resp.json()
                result["connected_email"] = (about_data.get("user") or {}).get("emailAddress")
                quota = about_data.get("storageQuota")
                result["storage_quota"] = quota

            quota_limit = int((quota or {}).get("limit") or 0) if quota and "limit" in quota else -1
            if auth_mode == "oauth2" or is_shared_drive or quota_limit != 0:
                result["can_upload_binary"] = True
            else:
                result["can_upload_binary"] = False
                result["error"] = (
                    "Service Account pada My Drive pribadi memiliki kuota 0 byte. "
                    "Hubungkan akun Google Anda via OAuth 2.0 agar file dapat diunggah dengan ukuran penuh."
                )
        except Exception as exc:
            result["error"] = str(exc)

        return result


google_drive_service = GoogleDriveService()

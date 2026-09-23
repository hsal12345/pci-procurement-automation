"""Packaging service for creating deterministic ZIP archives with cryptographic
SHA-256 manifests (manifest.json and human-readable MANIFEST.txt).
"""
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def compute_sha256(file_path: Path) -> str:
    """Computes hexadecimal SHA-256 hash of a file."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


class ZipPackager:
    """Packages generated procurement documents into a structured ZIP archive
    with machine-readable manifest.json and human-readable MANIFEST.txt.
    """

    def __init__(self, context: Dict[str, Any]):
        self.context = context

    def create_package_zip(
        self,
        artifact_files: List[Dict[str, Any]],
        output_dir: Path,
        zip_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """Assembles all generated artifact files, generates manifests,
        creates the compressed ZIP, and returns metadata for all artifacts.

        Each entry in artifact_files should be a dict:
        {
            "doc_code": str,      # e.g. "D01", "ALL", "CONSOLIDATED"
            "format": str,        # "XLSX", "DOCX", "PDF"
            "path": Path,
            "filename": str
        }
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        pkg = self.context.get("package", {})
        pkg_num = pkg.get("number", "PKG")
        clean_pkg_slug = "".join(c if c.isalnum() else "_" for c in pkg_num)
        rev_num = pkg.get("revision_number", 1)
        now_iso = datetime.now(timezone.utc).isoformat()

        if not zip_filename:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"{clean_pkg_slug}_REV{rev_num}_{timestamp_str}.zip"

        zip_path = output_dir / zip_filename

        # 1. Compute checksums and gather file entries
        manifest_entries = []
        for item in artifact_files:
            fpath = Path(item["path"])
            if fpath.exists():
                size = fpath.stat().st_size
                sha = compute_sha256(fpath)
                manifest_entries.append({
                    "doc_code": item.get("doc_code", "GEN"),
                    "format": item.get("format", "FILE"),
                    "filename": item.get("filename", fpath.name),
                    "file_path": str(fpath),
                    "size_bytes": size,
                    "sha256": sha,
                })

        # 2. Generate manifest.json
        manifest_data = {
            "package_number": pkg_num,
            "fiscal_year": pkg.get("fiscal_year", 2026),
            "quarter": pkg.get("quarter", 2),
            "revision_number": rev_num,
            "is_draft": self.context.get("is_draft", False),
            "generated_at": now_iso,
            "school_name": self.context.get("school", {}).get("name", ""),
            "vendor_name": self.context.get("company", {}).get("legal_name", ""),
            "grand_total": float(self.context.get("totals", {}).get("grand_total", 0)),
            "line_items_count": len(self.context.get("items", [])),
            "files_count": len(manifest_entries),
            "files": manifest_entries,
        }

        json_manifest_path = output_dir / "manifest.json"
        with open(json_manifest_path, "w", encoding="utf-8") as f_json:
            json.dump(manifest_data, f_json, indent=2, ensure_ascii=False)

        manifest_entries.append({
            "doc_code": "MANIFEST_JSON",
            "format": "JSON",
            "filename": "manifest.json",
            "file_path": str(json_manifest_path),
            "size_bytes": json_manifest_path.stat().st_size,
            "sha256": compute_sha256(json_manifest_path),
        })

        # 3. Generate human-readable MANIFEST.txt
        txt_manifest_path = output_dir / "MANIFEST.txt"
        with open(txt_manifest_path, "w", encoding="utf-8") as f_txt:
            f_txt.write("=" * 80 + "\n")
            f_txt.write("  CV PUSTAKA CEMERLANG INDONESIA - ARSIP DOKUMEN PENGADAAN & SPJ\n")
            f_txt.write("=" * 80 + "\n\n")
            f_txt.write(f"Nomor Paket     : {pkg_num}\n")
            f_txt.write(f"Revisi Ke       : {rev_num}\n")
            f_txt.write(f"Satuan Kerja    : {manifest_data['school_name']}\n")
            f_txt.write(f"Penyedia        : {manifest_data['vendor_name']}\n")
            f_txt.write(f"Tahun Anggaran  : {manifest_data['fiscal_year']} (Triwulan {manifest_data['quarter']})\n")
            f_txt.write(f"Grand Total     : Rp {self.context.get('totals', {}).get('grand_total_formatted', '0')}\n")
            f_txt.write(f"Status Dokumen  : {'DRAFT (BELUM DISETUJUI)' if manifest_data['is_draft'] else 'FINAL (DISETUJUI)'}\n")
            f_txt.write(f"Waktu Dibuat    : {now_iso}\n")
            f_txt.write(f"Jumlah Barang   : {manifest_data['line_items_count']} item\n\n")
            f_txt.write("-" * 80 + "\n")
            f_txt.write(f"{'NAMA FILE':<35} {'FORMAT':<8} {'UKURAN (B)':<12} {'SHA-256'}\n")
            f_txt.write("-" * 80 + "\n")
            for m in manifest_entries:
                f_txt.write(f"{m['filename']:<35} {m['format']:<8} {m['size_bytes']:<12} {m['sha256']}\n")
            f_txt.write("-" * 80 + "\n")

        manifest_entries.append({
            "doc_code": "MANIFEST_TXT",
            "format": "TXT",
            "filename": "MANIFEST.txt",
            "file_path": str(txt_manifest_path),
            "size_bytes": txt_manifest_path.stat().st_size,
            "sha256": compute_sha256(txt_manifest_path),
        })

        # 4. Create ZIP Archive
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for entry in manifest_entries:
                p = Path(entry["file_path"])
                # Place in appropriate subfolder based on format
                fmt = entry["format"].lower()
                if fmt in ["xlsx"]:
                    arcname = f"excel/{entry['filename']}"
                elif fmt in ["docx"]:
                    arcname = f"docx/{entry['filename']}"
                elif fmt in ["pdf"]:
                    arcname = f"pdf/{entry['filename']}"
                else:
                    arcname = entry["filename"]
                zf.write(p, arcname=arcname)

        zip_size = zip_path.stat().st_size
        zip_sha = compute_sha256(zip_path)

        zip_entry = {
            "doc_code": "ZIP",
            "format": "ZIP",
            "filename": zip_filename,
            "file_path": str(zip_path),
            "size_bytes": zip_size,
            "sha256": zip_sha,
        }

        return {
            "zip_file": zip_entry,
            "artifacts": manifest_entries + [zip_entry],
            "manifest": manifest_data,
        }

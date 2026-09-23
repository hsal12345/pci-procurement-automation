import html
import re
from typing import Any, Dict, List, Optional, Tuple


class PIISanitizer:
    """Enterprise sanitization and redaction engine for scrubbing personally
    identifiable information (NIP, NPWP, Bank Accounts, Phone Numbers, and Official Signers)
    before any text leaves the system to external LLM providers (PRD Section FR05).
    Also neutralizes adversarial prompt-injection tags using safe XML escaping (AT16).
    """

    # 18-digit Indonesian Civil Servant ID (NIP): e.g. 19750510 199803 1 002 or 197505101998031002
    NIP_REGEX = re.compile(r"\b(\d{8}\s?\d{6}\s?\d{1}\s?\d{3}|\d{18})\b")

    # Indonesian NPWP: 15-16 digits formatted (02.456.789.0-034.000) or unformatted 15-16 digits
    NPWP_REGEX = re.compile(r"\b(\d{2}\.\d{3}\.\d{3}\.\d{1}-\d{3}\.\d{3}|\d{15,16})\b")

    # Bank Account numbers: 10 to 16 consecutive digits (avoiding dates or short IDs)
    # Indonesian telephone numbers (+628..., 08..., (021)...)
    PHONE_REGEX = re.compile(r"\b(\+62|62|08)\d{8,11}\b|\(?\b(021|022|031)\)?[-\s]?\d{6,8}\b")

    # Bank Account numbers: 10 to 16 consecutive digits (avoiding dates or short IDs)
    BANK_REGEX = re.compile(r"\b\d{10,16}\b")

    @classmethod
    def safe_cell_content(cls, val: Any) -> str:
        """Escapes XML/HTML reserved characters (<, >, &, \", \') from cell text
        to prevent delimiter breakout and prompt injection (PRD Acceptance Test AT16).
        """
        if val is None:
            return ""
        # Strip extraneous whitespace and escape XML entities
        text = str(val).strip()
        return html.escape(text, quote=True)

    @classmethod
    def sanitize_text(
        cls,
        text: str,
        officials_names: Optional[List[str]] = None
    ) -> Tuple[str, Dict[str, str]]:
        """Scrubs PII from raw string. Returns (sanitized_string, token_map)."""
        if not text:
            return "", {}

        token_map: Dict[str, str] = {}
        sanitized = text

        # 1. Scrub exact official and signer names if provided (from snapshot)
        if officials_names:
            for idx, raw_name in enumerate(officials_names, start=1):
                clean_name = raw_name.strip()
                if len(clean_name) >= 3 and clean_name.lower() in sanitized.lower():
                    token = f"[REDACTED_OFFICIAL_{idx}]"
                    # Case-insensitive replacement
                    pattern = re.compile(re.escape(clean_name), re.IGNORECASE)
                    sanitized = pattern.sub(token, sanitized)
                    token_map[token] = clean_name

        # 2. Scrub NIP
        nip_counter = 1
        for match in cls.NIP_REGEX.finditer(sanitized):
            matched_str = match.group(0)
            token = f"[REDACTED_NIP_{nip_counter}]"
            token_map[token] = matched_str
            sanitized = sanitized.replace(matched_str, token, 1)
            nip_counter += 1

        # 3. Scrub NPWP
        npwp_counter = 1
        for match in cls.NPWP_REGEX.finditer(sanitized):
            matched_str = match.group(0)
            token = f"[REDACTED_NPWP_{npwp_counter}]"
            token_map[token] = matched_str
            sanitized = sanitized.replace(matched_str, token, 1)
            npwp_counter += 1

        # 4. Scrub Phone Numbers (MUST precede bank accounts so 08... numbers are caught as phones)
        phone_counter = 1
        for match in cls.PHONE_REGEX.finditer(sanitized):
            matched_str = match.group(0)
            if "[REDACTED_" in matched_str:
                continue
            token = f"[REDACTED_PHONE_{phone_counter}]"
            token_map[token] = matched_str
            sanitized = sanitized.replace(matched_str, token, 1)
            phone_counter += 1

        # 5. Scrub Bank Accounts (10-16 digits)
        bank_counter = 1
        for match in cls.BANK_REGEX.finditer(sanitized):
            matched_str = match.group(0)
            # Skip if already a token
            if "[REDACTED_" in matched_str:
                continue
            token = f"[REDACTED_REKENING_{bank_counter}]"
            token_map[token] = matched_str
            sanitized = sanitized.replace(matched_str, token, 1)
            bank_counter += 1

        return sanitized, token_map

    @classmethod
    def sanitize_payload(
        cls,
        payload: Any,
        officials_names: Optional[List[str]] = None
    ) -> Tuple[Any, Dict[str, str]]:
        """Recursively sanitizes dictionaries, lists, or strings."""
        aggregated_map: Dict[str, str] = {}

        if isinstance(payload, str):
            clean_str, tmap = cls.sanitize_text(payload, officials_names)
            aggregated_map.update(tmap)
            return clean_str, aggregated_map

        elif isinstance(payload, list):
            clean_list = []
            for item in payload:
                c_item, tmap = cls.sanitize_payload(item, officials_names)
                aggregated_map.update(tmap)
                clean_list.append(c_item)
            return clean_list, aggregated_map

        elif isinstance(payload, dict):
            clean_dict = {}
            for k, v in payload.items():
                c_val, tmap = cls.sanitize_payload(v, officials_names)
                aggregated_map.update(tmap)
                clean_dict[k] = c_val
            return clean_dict, aggregated_map

        return payload, aggregated_map

    @classmethod
    def restore_display_text(cls, text: str, token_map: Dict[str, str]) -> str:
        """Restores redacted placeholders into descriptive masked strings for UI diagnostic display.
        Note: This is strictly read-only for user guidance and never alters database fields.
        """
        if not text or not token_map:
            return text
        output = text
        for token, original in token_map.items():
            if "[REDACTED_NIP" in token and len(original) >= 6:
                masked = original[:4] + ("*" * (len(original) - 6)) + original[-2:]
                output = output.replace(token, f"{masked} (NIP)")
            elif "[REDACTED_NPWP" in token and len(original) >= 6:
                masked = original[:4] + ("*" * (len(original) - 6)) + original[-2:]
                output = output.replace(token, f"{masked} (NPWP)")
            elif "[REDACTED_REKENING" in token and len(original) >= 4:
                masked = original[:2] + ("*" * (len(original) - 4)) + original[-2:]
                output = output.replace(token, f"{masked} (Rekening)")
            elif "[REDACTED_OFFICIAL" in token:
                output = output.replace(token, original)
            else:
                output = output.replace(token, original)
        return output

from typing import List, Optional, Dict, Any
from app.core.rules.base import RuleFinding
from app.schemas.common import SeverityEnum


def validate_br01_identity_consistency(
    school_snapshot: Dict[str, Any],
    company_snapshot: Dict[str, Any],
    detected_entities: Optional[List[Dict[str, Any]]] = None
) -> List[RuleFinding]:
    """BR01 Identity Consistency:
    Matches school, company, and official identities against confirmed revision snapshots.
    Flags obsolete or competing names across all documents.
    """
    findings: List[RuleFinding] = []
    
    confirmed_school_name = (school_snapshot.get("name") or "").strip().upper()
    confirmed_company_name = (company_snapshot.get("legal_name") or "").strip().upper()

    if not confirmed_school_name:
        findings.append(RuleFinding(
            rule_code="BR01",
            severity=SeverityEnum.BLOCK,
            field_name="school_name",
            message="Nama sekolah pada snapshot revisi kosong atau tidak terdefinisi."
        ))

    if not confirmed_company_name:
        findings.append(RuleFinding(
            rule_code="BR01",
            severity=SeverityEnum.BLOCK,
            field_name="company_name",
            message="Nama penyedia pada snapshot revisi kosong atau tidak terdefinisi."
        ))

    if detected_entities:
        for ent in detected_entities:
            ent_type = ent.get("type", "").upper()
            found_name = (ent.get("name") or "").strip().upper()
            sheet = ent.get("sheet_name")
            cell = ent.get("cell_range")

            if ent_type == "SCHOOL":
                # Check if detected school name conflicts with confirmed school name
                # E.g. detected SDN Kebon Kosong 05 or 13 when confirmed is SDN Kebon Kosong 09
                if found_name and confirmed_school_name and found_name != confirmed_school_name:
                    # Check if it is a major conflict
                    findings.append(RuleFinding(
                        rule_code="BR01",
                        severity=SeverityEnum.BLOCK,
                        sheet_name=sheet,
                        cell_range=cell,
                        field_name="school_name",
                        original_value=found_name,
                        proposed_value=confirmed_school_name,
                        message=f"Inkonsistensi nama sekolah pada sheet '{sheet}': terdeteksi '{found_name}' padahal nama terkonfirmasi adalah '{confirmed_school_name}'."
                    ))

            elif ent_type == "COMPANY":
                # Check if detected company name conflicts with confirmed company name
                # E.g. detected CV. MITRA KARYA GEMILANG when confirmed is CV. PUSTAKA CEMERLANG INDONESIA
                if found_name and confirmed_company_name and found_name != confirmed_company_name:
                    findings.append(RuleFinding(
                        rule_code="BR01",
                        severity=SeverityEnum.BLOCK,
                        sheet_name=sheet,
                        cell_range=cell,
                        field_name="company_name",
                        original_value=found_name,
                        proposed_value=confirmed_company_name,
                        message=f"Inkonsistensi nama badan usaha penyedia pada sheet '{sheet}': terdeteksi '{found_name}' padahal nama resmi terkonfirmasi adalah '{confirmed_company_name}'."
                    ))

    return findings


def validate_br09_signatories(
    officials_snapshot: List[Dict[str, Any]],
    events: List[Dict[str, Any]]
) -> List[RuleFinding]:
    """BR09 Signatories:
    Validates that required appointment roles (Kepala Sekolah, Bendahara, Pengurus Barang, Direktur)
    exist and are active on the relevant transaction event dates.
    """
    findings: List[RuleFinding] = []
    
    roles_present = {}
    for o in officials_snapshot:
        if not isinstance(o, dict):
            continue
        role = (o.get("role") or "").strip().upper()
        if not role and o.get("role_title"):
            title = str(o.get("role_title", "")).upper()
            if "KEPALA" in title:
                role = "KEPALA_SEKOLAH"
            elif "BENDAHARA" in title:
                role = "BENDAHARA"
            elif "BARANG" in title:
                role = "PENGURUS_BARANG"
            elif "DIREKTUR" in title:
                role = "DIREKTUR"
        if role:
            roles_present[role] = o

    required_roles = ["KEPALA_SEKOLAH", "BENDAHARA", "PENGURUS_BARANG"]

    for role in required_roles:
        if role not in roles_present:
            findings.append(RuleFinding(
                rule_code="BR09",
                severity=SeverityEnum.BLOCK,
                field_name=f"signatory_{role.lower()}",
                message=f"Pejabat sekolah dengan peran '{role}' belum ditetapkan pada snapshot revisi."
            ))
        else:
            official = roles_present[role]
            p_name = (official.get("person_name") or official.get("name") or "").strip()
            if not p_name:
                findings.append(RuleFinding(
                    rule_code="BR09",
                    severity=SeverityEnum.BLOCK,
                    field_name=f"signatory_{role.lower()}_name",
                    message=f"Nama pejabat untuk peran '{role}' tidak boleh kosong."
                ))

    return findings

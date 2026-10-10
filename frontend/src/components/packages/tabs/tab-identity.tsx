"use client";

import { useState, useEffect } from "react";
import {
  PackageRevision,
  SchoolSnapshot,
  CompanySnapshot,
  OfficialSnapshotItem,
  TaxPolicySnapshotItem,
} from "@/types/package";
import { normalizeLeadingZeros } from "@/lib/formatters";
import { apiClient } from "@/lib/api-client";
import { CreateCompanyModal } from "@/components/packages/create-company-modal";
import {
  Building2,
  Landmark,
  UserCheck,
  ShieldAlert,
  CheckCircle2,
  AlertCircle,
  Plus,
  Trash2,
  Sparkles,
  RefreshCw,
  Loader2,
  X,
  UserPlus,
  Percent,
} from "lucide-react";

interface TabIdentityProps {
  revision: PackageRevision;
  isReadOnly: boolean;
  onIdentityChanged: (payload: {
    school_snapshot: SchoolSnapshot;
    company_snapshot: CompanySnapshot;
    officials_snapshot: OfficialSnapshotItem[];
    tax_policy_snapshot?: TaxPolicySnapshotItem[];
  }) => void;
}

const DEFAULT_OFFICIALS_TEMPLATE: OfficialSnapshotItem[] = [
  {
    role: "KEPALA_SEKOLAH",
    role_title: "Kepala Sekolah",
    person_name: "Drs. H. Mulyadi, M.Pd",
    name: "Drs. H. Mulyadi, M.Pd",
    nip: "196501011990031005",
    position_sk_number: "800/014/SK/2025",
  },
  {
    role: "BENDAHARA",
    role_title: "Bendahara BOS",
    person_name: "Siti Rahmawati, S.Pd",
    name: "Siti Rahmawati, S.Pd",
    nip: "198005122008012015",
    position_sk_number: "800/015/SK/2025",
  },
  {
    role: "PENGURUS_BARANG",
    role_title: "Pengurus Barang",
    person_name: "Sulistiawati",
    name: "Sulistiawati",
    nip: "197909092022212008",
    position_sk_number: "800/016/SK/2025",
  },
  {
    role: "DIREKTUR",
    role_title: "Direktur Rekanan",
    person_name: "Bambang Solifian",
    name: "Bambang Solifian",
    nip: null,
    position_sk_number: "Akta Notaris No. 12 Th 2020",
  },
];

function normalizeOfficials(raw?: OfficialSnapshotItem[] | null): OfficialSnapshotItem[] {
  if (!raw || raw.length === 0) {
    return [];
  }
  return raw.map((item) => {
    let role = (item.role || "").toUpperCase();
    if (!role && item.role_title) {
      const t = item.role_title.toUpperCase();
      if (t.includes("KEPALA")) role = "KEPALA_SEKOLAH";
      else if (t.includes("BENDAHARA")) role = "BENDAHARA";
      else if (t.includes("BARANG")) role = "PENGURUS_BARANG";
      else if (t.includes("DIREKTUR")) role = "DIREKTUR";
      else role = "PEJABAT";
    }
    const valName = item.person_name || item.name || "";
    return {
      ...item,
      role: role || "PEJABAT",
      role_title: item.role_title || formatRoleTitle(role),
      person_name: valName,
      name: valName,
      nip: item.nip ?? null,
      position_sk_number: item.position_sk_number || "",
    };
  });
}

function formatRoleTitle(role?: string): string {
  switch (role) {
    case "KEPALA_SEKOLAH":
      return "Kepala Sekolah";
    case "BENDAHARA":
      return "Bendahara BOS";
    case "PENGURUS_BARANG":
      return "Pengurus Barang";
    case "DIREKTUR":
      return "Direktur Rekanan";
    case "PEJABAT_PENGADAAN":
      return "Pejabat Pengadaan";
    case "PPHP":
      return "PPHP / Pemeriksa Barang";
    default:
      return role ? role.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "Pejabat";
  }
}

export function TabIdentity({
  revision,
  isReadOnly,
  onIdentityChanged: onParentIdentityChanged,
}: TabIdentityProps) {
  const [school, setSchool] = useState<SchoolSnapshot>(() => revision.school_snapshot || {});
  const [company, setCompany] = useState<CompanySnapshot>(() => revision.company_snapshot || {});
  const [officials, setOfficials] = useState<OfficialSnapshotItem[]>(() =>
    normalizeOfficials(revision.officials_snapshot)
  );
  const [taxPolicies, setTaxPolicies] = useState<TaxPolicySnapshotItem[]>(() => revision.tax_policy_snapshot || []);

  const onIdentityChanged = (payload: {
    school_snapshot: SchoolSnapshot;
    company_snapshot: CompanySnapshot;
    officials_snapshot: OfficialSnapshotItem[];
    tax_policy_snapshot?: TaxPolicySnapshotItem[];
  }) => {
    onParentIdentityChanged({
      school_snapshot: payload.school_snapshot,
      company_snapshot: payload.company_snapshot,
      officials_snapshot: payload.officials_snapshot,
      tax_policy_snapshot: payload.tax_policy_snapshot !== undefined ? payload.tax_policy_snapshot : taxPolicies,
    });
  };

  // Master Data
  const [masterSchools, setMasterSchools] = useState<any[]>([]);
  const [masterCompanies, setMasterCompanies] = useState<any[]>([]);
  const [isLoadingMasters, setIsLoadingMasters] = useState(false);

  // Add Official to Master Modal State
  const [showAddOfficialModal, setShowAddOfficialModal] = useState(false);
  const [showAddCompanyModal, setShowAddCompanyModal] = useState(false);
  const [newOfficialRole, setNewOfficialRole] = useState("KEPALA_SEKOLAH");
  const [newOfficialName, setNewOfficialName] = useState("");
  const [newOfficialNip, setNewOfficialNip] = useState("");
  const [newOfficialSk, setNewOfficialSk] = useState("");
  const [isSavingOfficial, setIsSavingOfficial] = useState(false);

  useEffect(() => {
    if (revision.school_snapshot) setSchool(revision.school_snapshot);
    if (revision.company_snapshot) setCompany(revision.company_snapshot);
    if (revision.officials_snapshot && revision.officials_snapshot.length > 0) {
      setOfficials(normalizeOfficials(revision.officials_snapshot));
    }
    if (revision.tax_policy_snapshot) {
      setTaxPolicies(revision.tax_policy_snapshot);
    }
  }, [revision]);

  // Load masters on mount
  useEffect(() => {
    async function fetchMasters() {
      setIsLoadingMasters(true);
      try {
        const [scs, cps] = await Promise.all([
          apiClient.getSchools().catch(() => []),
          apiClient.getCompanies().catch(() => []),
        ]);
        setMasterSchools(scs || []);
        setMasterCompanies(cps || []);
      } finally {
        setIsLoadingMasters(false);
      }
    }
    fetchMasters();
  }, []);

  const updateSchool = (field: keyof SchoolSnapshot, val: string) => {
    const updated = { ...school, [field]: val };
    setSchool(updated);
    onIdentityChanged({
      school_snapshot: updated,
      company_snapshot: company,
      officials_snapshot: officials,
    });
  };

  const updateCompany = (field: keyof CompanySnapshot, val: string) => {
    const updated = { ...company, [field]: val };
    setCompany(updated);
    onIdentityChanged({
      school_snapshot: school,
      company_snapshot: updated,
      officials_snapshot: officials,
    });
  };

  const updateOfficial = (idx: number, field: keyof OfficialSnapshotItem, val: string | null) => {
    const updated = [...officials];
    updated[idx] = { ...updated[idx], [field]: val };
    if (field === "name") {
      updated[idx].person_name = val || "";
    } else if (field === "person_name") {
      updated[idx].name = val || "";
    }
    setOfficials(updated);
    onIdentityChanged({
      school_snapshot: school,
      company_snapshot: company,
      officials_snapshot: updated,
    });
  };

  const handleSelectMasterSchool = async (schoolId: string) => {
    const sc = masterSchools.find((s) => s.id === schoolId);
    if (!sc) return;

    const updatedSchool: SchoolSnapshot = {
      ...school,
      name: sc.name,
      npsn: sc.npsn || school.npsn,
      address: sc.address || school.address,
      district: sc.subdistrict || school.district || "Kemayoran",
      regency: school.regency || "Kota Adm. Jakarta Pusat",
      province: school.province || "DKI Jakarta",
    };
    setSchool(updatedSchool);

    // Also load registered officials for this school
    try {
      const offs = await apiClient.getSchoolOfficials(sc.id);
      let updatedOfficials: OfficialSnapshotItem[] = [];
      const direktur = officials.find((o) => o.role === "DIREKTUR");

      if (offs && offs.length > 0) {
        const mappedSchoolOfficials: OfficialSnapshotItem[] = offs.map((o: any) => ({
          role: o.role,
          role_title: formatRoleTitle(o.role),
          person_name: o.person_name,
          name: o.person_name,
          nip: o.nip,
          position_sk_number: o.position_sk_number || "",
        }));

        if (direktur) {
          mappedSchoolOfficials.push(direktur);
        }
        updatedOfficials = mappedSchoolOfficials;
      } else {
        // Reset school officials so we don't leak the previous school's officials
        updatedOfficials = [
          {
            role: "KEPALA_SEKOLAH",
            role_title: "Kepala Sekolah",
            person_name: "",
            name: "",
            nip: "",
            position_sk_number: "",
          },
          {
            role: "BENDAHARA",
            role_title: "Bendahara BOS",
            person_name: "",
            name: "",
            nip: "",
            position_sk_number: "",
          },
          {
            role: "PENGURUS_BARANG",
            role_title: "Pengurus Barang",
            person_name: "",
            name: "",
            nip: "",
            position_sk_number: "",
          },
        ];
        if (direktur) {
          updatedOfficials.push(direktur);
        }
      }
      setOfficials(updatedOfficials);
      onIdentityChanged({
        school_snapshot: updatedSchool,
        company_snapshot: company,
        officials_snapshot: updatedOfficials,
      });
    } catch {
      onIdentityChanged({
        school_snapshot: updatedSchool,
        company_snapshot: company,
        officials_snapshot: officials,
      });
    }
  };

  const handleSelectMasterCompany = async (compId: string) => {
    const cp = masterCompanies.find((c) => c.id === compId);
    if (!cp) return;

    const updatedCompany: CompanySnapshot = {
      ...company,
      name: cp.legal_name || cp.name,
      npwp: cp.npwp || company.npwp,
      director_name: cp.director_name || company.director_name,
      bank_name: cp.bank_name || company.bank_name,
      bank_account_number: cp.bank_account_number || company.bank_account_number,
      bank_account_holder: cp.bank_account_holder || company.bank_account_holder,
    };
    setCompany(updatedCompany);

    let directorName = cp.director_name || "";
    let directorSk = cp.director_sk_number || "";
    let directorNip = null;

    try {
      const compOfficials = await apiClient.getCompanyOfficials(cp.id);
      const dir = compOfficials?.find((o: any) => o.role === "DIREKTUR") || compOfficials?.[0];
      if (dir) {
        directorName = dir.person_name || directorName;
        directorSk = dir.position_sk_number || directorSk;
        directorNip = dir.nip ?? null;
      }
    } catch {
      // fallback to company base fields
    }

    // Update DIREKTUR in officials list
    let foundDirektur = false;
    const updatedOfficials = officials.map((o) => {
      if (o.role === "DIREKTUR") {
        foundDirektur = true;
        return {
          ...o,
          person_name: directorName || o.person_name,
          name: directorName || o.name,
          nip: directorNip,
          position_sk_number: directorSk || o.position_sk_number,
        };
      }
      return o;
    });

    if (!foundDirektur && directorName) {
      updatedOfficials.push({
        role: "DIREKTUR",
        role_title: "Direktur Rekanan",
        person_name: directorName,
        name: directorName,
        nip: directorNip,
        position_sk_number: directorSk,
      });
    }

    setOfficials(updatedOfficials);

    onIdentityChanged({
      school_snapshot: school,
      company_snapshot: updatedCompany,
      officials_snapshot: updatedOfficials,
    });
  };

  const handleCompanyCreated = async (newComp: any) => {
    try {
      const cps = await apiClient.getCompanies();
      setMasterCompanies(cps || []);
      if (newComp?.id) {
        await handleSelectMasterCompany(newComp.id);
      }
    } catch {
      // ignore
    }
  };

  const handleLoadSchoolOfficials = async () => {
    const matched = masterSchools.find(
      (s) =>
        (school.npsn && s.npsn === school.npsn) ||
        s.name?.toLowerCase().trim() === school.name?.toLowerCase().trim()
    );
    if (!matched) {
      alert(
        "Sekolah saat ini belum terhubung dengan master data. Silakan pilih sekolah dari dropdown 'Pilih dari Master Sekolah' terlebih dahulu."
      );
      return;
    }

    try {
      const offs = await apiClient.getSchoolOfficials(matched.id);
      if (!offs || offs.length === 0) {
        alert("Belum ada pejabat penandatangan yang terdaftar di master untuk sekolah ini.");
        return;
      }
      const mappedSchoolOfficials: OfficialSnapshotItem[] = offs.map((o: any) => ({
        role: o.role,
        role_title: formatRoleTitle(o.role),
        person_name: o.person_name,
        name: o.person_name,
        nip: o.nip,
        position_sk_number: o.position_sk_number || "",
      }));

      const direktur = officials.find((o) => o.role === "DIREKTUR");
      if (direktur) mappedSchoolOfficials.push(direktur);

      setOfficials(mappedSchoolOfficials);
      onIdentityChanged({
        school_snapshot: school,
        company_snapshot: company,
        officials_snapshot: mappedSchoolOfficials,
      });
      alert(`Berhasil memuat ${offs.length} pejabat resmi dari master data.`);
    } catch (err: any) {
      alert(`Gagal memuat pejabat: ${err.message || err}`);
    }
  };

  const handleSaveOfficialToMaster = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newOfficialName.trim()) {
      alert("Nama lengkap pejabat wajib diisi.");
      return;
    }
    const matched = masterSchools.find(
      (s) =>
        (school.npsn && s.npsn === school.npsn) ||
        s.name?.toLowerCase().trim() === school.name?.toLowerCase().trim()
    );
    if (!matched) {
      alert(
        "Sekolah belum terhubung ke master data. Silakan pilih dari dropdown 'Pilih dari Master Sekolah' terlebih dahulu."
      );
      return;
    }

    setIsSavingOfficial(true);
    try {
      await apiClient.createSchoolOfficial(matched.id, {
        role: newOfficialRole,
        person_name: newOfficialName.trim(),
        nip: newOfficialNip.trim() || undefined,
        position_sk_number: newOfficialSk.trim() || undefined,
        valid_from: "2026-01-01",
      });

      // Update in local snapshot
      const updated = [...officials];
      const existingIdx = updated.findIndex((o) => o.role === newOfficialRole);
      const newOffItem: OfficialSnapshotItem = {
        role: newOfficialRole,
        role_title: formatRoleTitle(newOfficialRole),
        person_name: newOfficialName.trim(),
        name: newOfficialName.trim(),
        nip: newOfficialNip.trim() || null,
        position_sk_number: newOfficialSk.trim(),
      };

      if (existingIdx >= 0) {
        updated[existingIdx] = newOffItem;
      } else {
        updated.push(newOffItem);
      }

      setOfficials(updated);
      onIdentityChanged({
        school_snapshot: school,
        company_snapshot: company,
        officials_snapshot: updated,
      });

      setShowAddOfficialModal(false);
      setNewOfficialName("");
      setNewOfficialNip("");
      setNewOfficialSk("");
      alert(
        `Pejabat ${newOfficialName} (${formatRoleTitle(newOfficialRole)}) berhasil didaftarkan ke master sekolah.`
      );
    } catch (err: any) {
      alert(`Gagal mendaftarkan pejabat: ${err.message || err}`);
    } finally {
      setIsSavingOfficial(false);
    }
  };

  const handleApplyDefaultOfficials = () => {
    setOfficials(DEFAULT_OFFICIALS_TEMPLATE);
    onIdentityChanged({
      school_snapshot: school,
      company_snapshot: company,
      officials_snapshot: DEFAULT_OFFICIALS_TEMPLATE,
    });
  };

  const handleAddOfficial = () => {
    const newOfficial: OfficialSnapshotItem = {
      role: "PEJABAT_PENGADAAN",
      role_title: "Pejabat Pengadaan",
      person_name: "",
      name: "",
      nip: "",
      position_sk_number: "",
    };
    const updated = [...officials, newOfficial];
    setOfficials(updated);
    onIdentityChanged({
      school_snapshot: school,
      company_snapshot: company,
      officials_snapshot: updated,
    });
  };

  const handleRemoveOfficial = (idx: number) => {
    const updated = officials.filter((_, i) => i !== idx);
    setOfficials(updated);
    onIdentityChanged({
      school_snapshot: school,
      company_snapshot: company,
      officials_snapshot: updated,
    });
  };

  // Tax Policy Handlers (BR06)
  const handleApplyPresetTax = (preset: "PPN_11" | "PPN_PPH" | "ZERO") => {
    let updated: TaxPolicySnapshotItem[] = [];
    if (preset === "PPN_11") {
      updated = [
        {
          tax_type: "PPN",
          rate: "0.11",
          rate_percent: 11,
          is_inclusive: false,
          withholding_rule: "NONE",
          rounding_rule: "ROUND_HALF_UP",
        },
      ];
    } else if (preset === "PPN_PPH") {
      updated = [
        {
          tax_type: "PPN",
          rate: "0.11",
          rate_percent: 11,
          is_inclusive: false,
          withholding_rule: "NONE",
          rounding_rule: "ROUND_HALF_UP",
        },
        {
          tax_type: "PPH22",
          rate: "0.015",
          rate_percent: 1.5,
          is_inclusive: false,
          withholding_rule: "WITHHOLD_FROM_PAYABLE",
          rounding_rule: "ROUND_HALF_UP",
        },
      ];
    } else if (preset === "ZERO") {
      updated = [
        {
          tax_type: "PPN",
          rate: "0",
          rate_percent: 0,
          is_inclusive: false,
          withholding_rule: "NONE",
          rounding_rule: "ROUND_HALF_UP",
          notes: "Bebas PPN",
        },
      ];
    }
    setTaxPolicies(updated);
    onIdentityChanged({
      school_snapshot: school,
      company_snapshot: company,
      officials_snapshot: officials,
      tax_policy_snapshot: updated,
    });
  };

  const handleRemoveTaxPolicy = (idx: number) => {
    const updated = taxPolicies.filter((_, i) => i !== idx);
    setTaxPolicies(updated);
    onIdentityChanged({
      school_snapshot: school,
      company_snapshot: company,
      officials_snapshot: officials,
      tax_policy_snapshot: updated,
    });
  };

  const handleAddCustomTaxPolicy = () => {
    const newPolicy: TaxPolicySnapshotItem = {
      tax_type: "PPN",
      rate: "0.11",
      rate_percent: 11,
      is_inclusive: false,
      withholding_rule: "NONE",
      rounding_rule: "ROUND_HALF_UP",
    };
    const updated = [...taxPolicies, newPolicy];
    setTaxPolicies(updated);
    onIdentityChanged({
      school_snapshot: school,
      company_snapshot: company,
      officials_snapshot: officials,
      tax_policy_snapshot: updated,
    });
  };

  const updateTaxPolicyField = (idx: number, field: keyof TaxPolicySnapshotItem, val: any) => {
    const updated = [...taxPolicies];
    const item = { ...updated[idx], [field]: val };
    if (field === "withholding_rule") {
      item.is_withholding = val !== "NONE";
    }
    updated[idx] = item;
    setTaxPolicies(updated);
    onIdentityChanged({
      school_snapshot: school,
      company_snapshot: company,
      officials_snapshot: officials,
      tax_policy_snapshot: updated,
    });
  };

  const updateTaxPolicyRate = (idx: number, ratePctStr: string) => {
    const ratePct = parseFloat(ratePctStr) || 0;
    const rateDec = (ratePct / 100).toString();
    const updated = [...taxPolicies];
    updated[idx] = {
      ...updated[idx],
      rate_percent: ratePct,
      rate: rateDec,
    };
    setTaxPolicies(updated);
    onIdentityChanged({
      school_snapshot: school,
      company_snapshot: company,
      officials_snapshot: officials,
      tax_policy_snapshot: updated,
    });
  };

  // Required roles check for BR09
  const hasKepalaSekolah = officials.some(
    (o) => o.role === "KEPALA_SEKOLAH" && (o.person_name || o.name)?.trim()
  );
  const hasBendahara = officials.some(
    (o) => o.role === "BENDAHARA" && (o.person_name || o.name)?.trim()
  );
  const hasPengurusBarang = officials.some(
    (o) => o.role === "PENGURUS_BARANG" && (o.person_name || o.name)?.trim()
  );
  const isBR09Satisfied = hasKepalaSekolah && hasBendahara && hasPengurusBarang;

  return (
    <div className="p-6 max-w-5xl space-y-6 text-xs font-sans">
      {/* 1. School Information (Lembaga Penerima SPJ) */}
      <div className="border border-border rounded-lg bg-card p-4 space-y-4">
        <div className="flex flex-wrap items-center justify-between border-b border-border/80 pb-2.5 gap-2">
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-primary" />
            <h3 className="font-semibold text-foreground text-sm">
              Identitas Sekolah & Lembaga Penerima (BR01)
            </h3>
          </div>

          {/* Master School Quick Selector */}
          {!isReadOnly && masterSchools.length > 0 && (
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] font-mono text-muted-foreground">Pilih dari Master:</span>
              <select
                onChange={(e) => handleSelectMasterSchool(e.target.value)}
                defaultValue=""
                className="px-2 py-1 bg-background border border-border rounded text-[11px] outline-none focus:ring-1 focus:ring-ring font-sans"
              >
                <option value="" disabled>
                  -- Pilih Sekolah Terdaftar --
                </option>
                {masterSchools.map((sc) => (
                  <option key={sc.id} value={sc.id}>
                    {sc.name} {sc.npsn ? `(${sc.npsn})` : ""}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
              Nama Sekolah (SD/SMP)
            </label>
            <input
              type="text"
              disabled={isReadOnly}
              value={school.name || ""}
              onChange={(e) => updateSchool("name", e.target.value)}
              placeholder="Contoh: SDN 01 Rawamangun"
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-sans"
            />
          </div>

          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
              NPSN (8 Digit)
            </label>
            <input
              type="text"
              disabled={isReadOnly}
              value={school.npsn || ""}
              onChange={(e) => updateSchool("npsn", normalizeLeadingZeros(e.target.value, 8))}
              placeholder="20101234"
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-mono tabular-nums"
            />
          </div>

          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
              Alamat Lengkap
            </label>
            <input
              type="text"
              disabled={isReadOnly}
              value={school.address || ""}
              onChange={(e) => updateSchool("address", e.target.value)}
              placeholder="Jl. Raya No. 12"
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-sans"
            />
          </div>

          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
              Kecamatan
            </label>
            <input
              type="text"
              disabled={isReadOnly}
              value={school.district || "Kemayoran"}
              onChange={(e) => updateSchool("district", e.target.value)}
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-sans"
            />
          </div>

          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
              Kota / Kabupaten
            </label>
            <input
              type="text"
              disabled={isReadOnly}
              value={school.regency || "Kota Adm. Jakarta Pusat"}
              onChange={(e) => updateSchool("regency", e.target.value)}
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-sans"
            />
          </div>

          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
              Provinsi
            </label>
            <input
              type="text"
              disabled={isReadOnly}
              value={school.province || "DKI Jakarta"}
              onChange={(e) => updateSchool("province", e.target.value)}
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-sans"
            />
          </div>
        </div>
      </div>

      {/* 2. Company Information (CV Pustaka Cemerlang Indonesia) */}
      <div className="border border-border rounded-lg bg-card p-4 space-y-4">
        <div className="flex flex-wrap items-center justify-between border-b border-border/80 pb-2.5 gap-2">
          <div className="flex items-center gap-2">
            <Landmark className="w-4 h-4 text-emerald-400" />
            <h3 className="font-semibold text-foreground text-sm">
              Identitas Rekanan Penyedia Pengadaan (CV PCI)
            </h3>
          </div>

          {/* Master Company Quick Selector */}
          {!isReadOnly && (
            <div className="flex items-center gap-2">
              {masterCompanies.length > 0 && (
                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] font-mono text-muted-foreground">Pilih Rekanan:</span>
                  <select
                    onChange={(e) => handleSelectMasterCompany(e.target.value)}
                    defaultValue=""
                    className="px-2 py-1 bg-background border border-border rounded text-[11px] outline-none focus:ring-1 focus:ring-ring font-sans"
                  >
                    <option value="" disabled>
                      -- Pilih Badan Usaha Rekanan --
                    </option>
                    {masterCompanies.map((cp) => (
                      <option key={cp.id} value={cp.id}>
                        {cp.legal_name || cp.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <button
                type="button"
                onClick={() => setShowAddCompanyModal(true)}
                className="flex items-center gap-1 text-[11px] font-mono px-2 py-1 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/25 transition font-medium"
                title="Tambah Badan Usaha Rekanan Baru"
              >
                <Plus className="w-3 h-3 text-emerald-400" />
                <span>+ Tambah Rekanan</span>
              </button>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
              Nama Perusahaan
            </label>
            <input
              type="text"
              disabled={isReadOnly}
              value={company.name || "CV Pustaka Cemerlang Indonesia"}
              onChange={(e) => updateCompany("name", e.target.value)}
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-sans"
            />
          </div>

          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
              NPWP Perusahaan (16 Digit Text)
            </label>
            <input
              type="text"
              disabled={isReadOnly}
              value={company.npwp || "01.234.567.8-012.000"}
              onChange={(e) => updateCompany("npwp", e.target.value)}
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-mono tabular-nums"
            />
          </div>

          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
              Direktur Utama
            </label>
            <input
              type="text"
              disabled={isReadOnly}
              value={company.director_name || "Bambang Solifian"}
              onChange={(e) => updateCompany("director_name", e.target.value)}
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-sans"
            />
          </div>

          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
              Nama Bank Rekanan
            </label>
            <input
              type="text"
              disabled={isReadOnly}
              value={company.bank_name || "Bank BJB / Bank Mandiri"}
              onChange={(e) => updateCompany("bank_name", e.target.value)}
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-sans"
            />
          </div>

          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
              Nomor Rekening Bank (Preserve 0)
            </label>
            <input
              type="text"
              disabled={isReadOnly}
              value={company.bank_account_number || "0012345678901"}
              onChange={(e) => updateCompany("bank_account_number", e.target.value)}
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-mono tabular-nums"
            />
          </div>

          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
              Atas Nama Rekening
            </label>
            <input
              type="text"
              disabled={isReadOnly}
              value={company.bank_account_holder || "CV Pustaka Cemerlang Indonesia"}
              onChange={(e) => updateCompany("bank_account_holder", e.target.value)}
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-sans"
            />
          </div>
        </div>
      </div>

      {/* 3. Pejabat Penandatangan & SK Penugasan (BR09) */}
      <div className="border border-border rounded-lg bg-card p-4 space-y-4">
        <div className="flex flex-wrap items-center justify-between border-b border-border/80 pb-2.5 gap-2">
          <div className="flex items-center gap-2">
            <UserCheck className="w-4 h-4 text-sky-400" />
            <h3 className="font-semibold text-foreground text-sm">
              Pejabat Penandatangan & Validasi SK (BR09)
            </h3>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {isBR09Satisfied ? (
              <span className="inline-flex items-center gap-1.5 text-[11px] font-mono text-emerald-300 bg-emerald-500/15 px-2.5 py-1 rounded border border-emerald-500/30 font-semibold">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>BR09 Lolos (3 Pejabat Sekolah Terisi)</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 text-[11px] font-mono text-rose-300 bg-rose-500/15 px-2.5 py-1 rounded border border-rose-500/30 font-semibold">
                <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                <span>BR09 Belum Lengkap</span>
              </span>
            )}

            {!isReadOnly && (
              <>
                <button
                  type="button"
                  onClick={handleLoadSchoolOfficials}
                  className="flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded bg-sky-500/15 text-sky-300 border border-sky-500/30 hover:bg-sky-500/25 transition font-medium"
                  title="Ambil pejabat terdaftar di master data sekolah ini"
                >
                  <RefreshCw className="w-3 h-3 text-sky-400" />
                  <span>Muat Pejabat dari Master</span>
                </button>

                <button
                  type="button"
                  onClick={() => setShowAddOfficialModal(true)}
                  className="flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/25 transition font-medium"
                  title="Daftarkan pejabat baru ke master sekolah"
                >
                  <UserPlus className="w-3 h-3 text-emerald-400" />
                  <span>+ Daftarkan Pejabat ke Master</span>
                </button>

                <button
                  type="button"
                  onClick={handleApplyDefaultOfficials}
                  className="flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded bg-muted text-foreground border border-border hover:bg-muted/80 transition font-medium"
                  title="Gunakan template awal SDN KK 09"
                >
                  <Sparkles className="w-3 h-3 text-amber-400" />
                  <span>Template KK 09</span>
                </button>
              </>
            )}
          </div>
        </div>

        {/* Required Roles Status Badges */}
        <div className="grid grid-cols-3 gap-2.5 font-mono text-[11px]">
          <div
            className={`p-2.5 rounded border flex items-center justify-between font-medium ${
              hasKepalaSekolah
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                : "bg-rose-500/10 border-rose-500/30 text-rose-300"
            }`}
          >
            <span>1. Kepala Sekolah:</span>
            <span className="font-bold">
              {hasKepalaSekolah ? "OK" : "Wajib Diisi"}
            </span>
          </div>

          <div
            className={`p-2.5 rounded border flex items-center justify-between font-medium ${
              hasBendahara
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                : "bg-rose-500/10 border-rose-500/30 text-rose-300"
            }`}
          >
            <span>2. Bendahara BOS:</span>
            <span className="font-bold">
              {hasBendahara ? "OK" : "Wajib Diisi"}
            </span>
          </div>

          <div
            className={`p-2.5 rounded border flex items-center justify-between font-medium ${
              hasPengurusBarang
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                : "bg-rose-500/10 border-rose-500/30 text-rose-300"
            }`}
          >
            <span>3. Pengurus Barang:</span>
            <span className="font-bold">
              {hasPengurusBarang ? "OK" : "Wajib Diisi"}
            </span>
          </div>
        </div>

        {/* Officials Form List */}
        <div className="divide-y divide-border/60">
          <div className="py-1.5 grid grid-cols-12 gap-2 text-[10px] font-mono uppercase text-muted-foreground font-semibold">
            <div className="col-span-3">Jabatan / Peran (BR09)</div>
            <div className="col-span-3">Nama Lengkap Pejabat</div>
            <div className="col-span-3">NIP (18 Digit Text)</div>
            <div className="col-span-2">No. SK Penugasan</div>
            <div className="col-span-1 text-center">Aksi</div>
          </div>

          {officials.map((off, idx) => {
            const isCoreRole = [
              "KEPALA_SEKOLAH",
              "BENDAHARA",
              "PENGURUS_BARANG",
              "DIREKTUR",
            ].includes(off.role || "");

            return (
              <div
                key={`${off.role || off.role_title}-${idx}`}
                className="py-2 grid grid-cols-12 gap-2 items-center"
              >
                <div className="col-span-3">
                  <div className="font-mono font-semibold text-foreground text-[11px]">
                    {off.role_title || formatRoleTitle(off.role)}
                  </div>
                  <span className="text-[10px] font-mono text-muted-foreground">
                    Kode: {off.role || "PEJABAT"}
                  </span>
                </div>

                <div className="col-span-3">
                  <input
                    type="text"
                    disabled={isReadOnly}
                    value={off.person_name || off.name || ""}
                    onChange={(e) => updateOfficial(idx, "name", e.target.value)}
                    placeholder="Nama Lengkap Pejabat"
                    className="w-full px-2 py-1 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-sans"
                  />
                </div>

                <div className="col-span-3">
                  <input
                    type="text"
                    disabled={isReadOnly || off.nip === null}
                    value={off.nip || ""}
                    onChange={(e) =>
                      updateOfficial(idx, "nip", normalizeLeadingZeros(e.target.value, 18))
                    }
                    placeholder={off.nip === null ? "Non-PNS (Rekanan)" : "NIP (18 Digit Text)"}
                    className="w-full px-2 py-1 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-mono tabular-nums disabled:bg-muted/40"
                  />
                </div>

                <div className="col-span-2">
                  <input
                    type="text"
                    disabled={isReadOnly}
                    value={off.position_sk_number || ""}
                    onChange={(e) => updateOfficial(idx, "position_sk_number", e.target.value)}
                    placeholder="Nomor SK"
                    className="w-full px-2 py-1 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-mono"
                  />
                </div>

                <div className="col-span-1 text-center">
                  {!isCoreRole && !isReadOnly ? (
                    <button
                      type="button"
                      onClick={() => handleRemoveOfficial(idx)}
                      className="p-1 rounded text-muted-foreground hover:text-destructive hover:bg-muted transition"
                      title="Hapus Pejabat"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  ) : (
                    <span className="text-[10px] font-mono text-muted-foreground">-</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Add Official Row Button */}
        {!isReadOnly && (
          <div className="pt-2 flex items-center justify-between border-t border-border/80">
            <button
              type="button"
              onClick={handleAddOfficial}
              className="flex items-center gap-1 px-2.5 py-1 text-xs font-mono rounded border border-dashed border-border hover:border-primary text-muted-foreground hover:text-foreground transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Tambah Pejabat Tambahan (PPHP / Tim BOS)</span>
            </button>
            <span className="text-[10px] text-muted-foreground font-mono">
              * Perubahan tersimpan ke draf dan dapat dikomit dengan tombol Simpan Perubahan di atas
            </span>
          </div>
        )}
      </div>

      {/* 4. Kebijakan Perpajakan Aktif (Tax Policy - BR06) */}
      <div className="border border-border rounded-lg bg-card p-4 space-y-4">
        <div className="flex flex-wrap items-center justify-between border-b border-border/80 pb-2.5 gap-2">
          <div className="flex items-center gap-2">
            <Percent className="w-4 h-4 text-amber-400" />
            <h3 className="font-semibold text-foreground text-sm">
              Kebijakan Perpajakan Aktif (Tax Policy - BR06)
            </h3>
          </div>

          <div className="flex items-center gap-2">
            {taxPolicies.length > 0 ? (
              <span className="flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-semibold">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>{taxPolicies.length} Kebijakan Pajak Aktif</span>
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded bg-red-500/15 text-red-300 border border-red-500/30 font-bold animate-pulse">
                <AlertCircle className="w-3.5 h-3.5 text-red-400" />
                <span>BELUM DITETAPKAN (BR06 BLOCK)</span>
              </span>
            )}
          </div>
        </div>

        <p className="text-[11px] text-muted-foreground leading-relaxed">
          Sesuai PRD Batasan Pilot & Validasi BR06, paket revisi wajib menetapkan kebijakan pajak efektif yang disetujui untuk menghitung PPN dan PPh secara akurat dan sah.
        </p>

        {/* Quick Presets */}
        {!isReadOnly && (
          <div className="p-3 bg-muted/40 border border-border rounded-md space-y-2">
            <div className="text-[11px] font-mono font-semibold text-foreground flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span>Terapkan Template Kebijakan Pajak Cepat:</span>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                id="btn-tax-preset-ppn11"
                onClick={() => handleApplyPresetTax("PPN_11")}
                className="px-3 py-1.5 rounded text-xs font-semibold bg-primary text-primary-foreground hover:bg-primary/90 transition shadow-sm flex items-center gap-1"
              >
                <span>⚡ Standar BOS (PPN 11%)</span>
              </button>

              <button
                type="button"
                id="btn-tax-preset-ppn-pph"
                onClick={() => handleApplyPresetTax("PPN_PPH")}
                className="px-3 py-1.5 rounded text-xs font-semibold bg-secondary text-secondary-foreground hover:bg-secondary/80 border border-border transition flex items-center gap-1"
              >
                <span>⚡ Lengkap (PPN 11% + PPh 22 1.5%)</span>
              </button>

              <button
                type="button"
                id="btn-tax-preset-zero"
                onClick={() => handleApplyPresetTax("ZERO")}
                className="px-3 py-1.5 rounded text-xs border border-border bg-card hover:bg-muted text-foreground transition font-medium"
              >
                <span>Bebas Pajak (PPN 0%)</span>
              </button>

              <button
                type="button"
                id="btn-add-custom-tax"
                onClick={handleAddCustomTaxPolicy}
                className="px-3 py-1.5 rounded text-xs border border-dashed border-border hover:border-primary text-foreground hover:text-primary transition flex items-center gap-1 font-mono font-medium"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Tambah Baris Pajak</span>
              </button>
            </div>
          </div>
        )}

        {/* Tax Policies Table */}
        {taxPolicies.length === 0 ? (
          <div className="p-4 border border-dashed border-red-500/40 rounded-md bg-red-500/10 text-center space-y-2">
            <p className="text-xs text-red-300 font-semibold">
              Belum ada kebijakan pajak yang dipilih pada snapshot revisi ini.
            </p>
            <p className="text-[11px] text-muted-foreground">
              Klik salah satu tombol preset di atas (misal <strong>Standar BOS PPN 11%</strong>) untuk menetapkan kebijakan pajak dan membuka blokir BR06.
            </p>
          </div>
        ) : (
          <div className="border border-border rounded-md overflow-hidden shadow-sm">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/90 border-b border-border text-[11px] uppercase font-mono font-bold text-slate-200">
                <tr>
                  <th className="px-3 py-2 w-10 text-center">No</th>
                  <th className="px-3 py-2 min-w-[160px]">Jenis Pajak</th>
                  <th className="px-3 py-2 w-28 text-right">Tarif Efektif</th>
                  <th className="px-3 py-2 min-w-[220px]">Perlakuan Sifat</th>
                  <th className="px-3 py-2 w-36">Pembulatan</th>
                  {!isReadOnly && <th className="px-3 py-2 w-16 text-center">Aksi</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60 font-mono text-[11px]">
                {taxPolicies.map((tp, idx) => {
                  const ratePct =
                    tp.rate_percent != null
                      ? tp.rate_percent
                      : Number(tp.rate) < 1 && Number(tp.rate) > 0
                      ? Number(tp.rate) * 100
                      : Number(tp.rate) || 0;

                  const isWithholding =
                    tp.is_withholding ||
                    (tp.withholding_rule && tp.withholding_rule !== "NONE");

                  return (
                    <tr key={idx} className="hover:bg-muted/20 transition">
                      <td className="px-3 py-2 text-center text-muted-foreground font-bold">
                        {idx + 1}
                      </td>
                      <td className="px-3 py-2">
                        {isReadOnly ? (
                          <span className="font-bold text-foreground">{tp.tax_type}</span>
                        ) : (
                          <select
                            value={tp.tax_type}
                            onChange={(e) => updateTaxPolicyField(idx, "tax_type", e.target.value)}
                            className="w-full px-2 py-1 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-mono"
                          >
                            <option value="PPN">PPN (Pajak Pertambahan Nilai)</option>
                            <option value="PPH22">PPh Pasal 22 (Pengadaan Barang)</option>
                            <option value="PPH23">PPh Pasal 23 (Jasa)</option>
                            <option value="PAJAK_DAERAH">Pajak Daerah / PB1</option>
                          </select>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right">
                        {isReadOnly ? (
                          <span className="font-bold text-foreground">{ratePct}%</span>
                        ) : (
                          <div className="flex items-center justify-end gap-1">
                            <input
                              type="number"
                              step="0.1"
                              min="0"
                              max="100"
                              value={ratePct}
                              onChange={(e) => updateTaxPolicyRate(idx, e.target.value)}
                              className="w-16 px-2 py-1 bg-background border border-border rounded text-xs text-right outline-none focus:ring-1 focus:ring-ring font-mono"
                            />
                            <span>%</span>
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        {isReadOnly ? (
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium border ${
                              isWithholding
                                ? "bg-purple-500/15 text-purple-300 border-purple-500/40"
                                : "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
                            }`}
                          >
                            {isWithholding
                              ? "Potong dari Rekanan (Withholding)"
                              : "Ditambahkan ke Subtotal (Aditif)"}
                          </span>
                        ) : (
                          <select
                            value={isWithholding ? "WITHHOLD_FROM_PAYABLE" : "NONE"}
                            onChange={(e) =>
                              updateTaxPolicyField(idx, "withholding_rule", e.target.value)
                            }
                            className="w-full px-2 py-1 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
                          >
                            <option value="NONE">Ditambahkan ke Subtotal (Aditif - Beban Sekolah)</option>
                            <option value="WITHHOLD_FROM_PAYABLE">
                              Dipotong dari Rekanan (Withholding / Net Payable)
                            </option>
                          </select>
                        )}
                      </td>
                      <td className="px-3 py-2 text-muted-foreground font-sans">
                        Bulat ke Rupiah Terdekat
                      </td>
                      {!isReadOnly && (
                        <td className="px-3 py-2 text-center">
                          <button
                            type="button"
                            onClick={() => handleRemoveTaxPolicy(idx)}
                            className="p-1.5 rounded text-muted-foreground hover:text-red-400 hover:bg-red-500/15 transition"
                            title="Hapus Aturan Pajak"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Quick Modal: Register Official to Master */}
      {showAddOfficialModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-card border border-border rounded-lg shadow-2xl w-full max-w-md overflow-hidden">
            <div className="flex items-center justify-between border-b border-border px-4 py-3 bg-muted/30">
              <div className="flex items-center gap-2">
                <UserPlus className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-semibold text-foreground">
                  Daftarkan Pejabat ke Master Sekolah
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowAddOfficialModal(false)}
                className="text-muted-foreground hover:text-foreground p-1 rounded hover:bg-muted"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveOfficialToMaster} className="p-4 space-y-3 text-xs font-sans">
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Pejabat yang didaftarkan akan tersimpan permanen di master data sekolah{" "}
                <strong>{school.name || "terpilih"}</strong> untuk digunakan pada paket-paket berikutnya.
              </p>

              <div>
                <label className="block text-[10px] uppercase font-mono text-muted-foreground mb-1">
                  Peran / Jabatan Penugasan
                </label>
                <select
                  value={newOfficialRole}
                  onChange={(e) => setNewOfficialRole(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-sans"
                >
                  <option value="KEPALA_SEKOLAH">Kepala Sekolah (Penanggung Jawab)</option>
                  <option value="BENDAHARA">Bendahara BOS</option>
                  <option value="PENGURUS_BARANG">Pengurus Barang / Pengelola Sarpras</option>
                  <option value="PEJABAT_PENGADAAN">Pejabat Pengadaan</option>
                  <option value="PPHP">PPHP / Pemeriksa Barang</option>
                </select>
              </div>

              <div>
                <label className="block text-[10px] uppercase font-mono text-muted-foreground mb-1">
                  Nama Lengkap & Gelar
                </label>
                <input
                  type="text"
                  value={newOfficialName}
                  onChange={(e) => setNewOfficialName(e.target.value)}
                  placeholder="Contoh: Drs. H. Ahmad Fauzi, M.Pd"
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-sans"
                />
              </div>

              <div>
                <label className="block text-[10px] uppercase font-mono text-muted-foreground mb-1">
                  NIP (18 Digit Angka)
                </label>
                <input
                  type="text"
                  value={newOfficialNip}
                  onChange={(e) => setNewOfficialNip(normalizeLeadingZeros(e.target.value, 18))}
                  placeholder="197501012000031002"
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-mono tabular-nums"
                />
              </div>

              <div>
                <label className="block text-[10px] uppercase font-mono text-muted-foreground mb-1">
                  Nomor SK Pengangkatan / Penugasan
                </label>
                <input
                  type="text"
                  value={newOfficialSk}
                  onChange={(e) => setNewOfficialSk(e.target.value)}
                  placeholder="Contoh: 800/014/SK/2026"
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-mono"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowAddOfficialModal(false)}
                  className="px-3 py-1.5 text-xs border border-border rounded bg-muted/40 hover:bg-muted text-muted-foreground"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={isSavingOfficial}
                  className="px-4 py-1.5 text-xs font-semibold rounded bg-emerald-600 text-white hover:bg-emerald-500 transition disabled:opacity-50 flex items-center gap-1"
                >
                  {isSavingOfficial && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>Daftarkan ke Master</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create Company Modal */}
      {showAddCompanyModal && (
        <CreateCompanyModal
          isOpen={showAddCompanyModal}
          onClose={() => setShowAddCompanyModal(false)}
          onCreated={handleCompanyCreated}
        />
      )}
    </div>
  );
}

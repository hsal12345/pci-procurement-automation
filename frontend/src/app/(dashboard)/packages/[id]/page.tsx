"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiClient, getCurrentRole, ApiError } from "@/lib/api-client";
import { PackageItem, RevisionLine, UserRole } from "@/types/package";
import { ValidationRun } from "@/types/validation";
import { WorkspaceHeader } from "@/components/packages/workspace-header";
import { TabIdentity } from "@/components/packages/tabs/tab-identity";
import { TabItems } from "@/components/packages/tabs/tab-items";
import { TabDatesNumbers } from "@/components/packages/tabs/tab-dates-numbers";
import { TabLogistics } from "@/components/packages/tabs/tab-logistics";
import { TabInspection } from "@/components/packages/tabs/tab-inspection";
import { TabDocuments } from "@/components/packages/tabs/tab-documents";
import { TabAudit } from "@/components/packages/tabs/tab-audit";
import { ApprovalModal } from "@/components/approvals/approval-modal";
import { ConflictModal } from "@/components/packages/conflict-modal";
import { ReopenModal } from "@/components/packages/reopen-modal";
import { CancelModal } from "@/components/packages/cancel-modal";
import {
  FileText,
  ShoppingBag,
  Calendar,
  Truck,
  CheckSquare,
  Archive,
  History,
  AlertCircle,
  Loader2,
} from "lucide-react";

const TABS = [
  { key: "identity", label: "1. Identitas", icon: FileText },
  { key: "items", label: "2. Barang & Harga", icon: ShoppingBag },
  { key: "dates", label: "3. Tanggal & Nomor", icon: Calendar },
  { key: "logistics", label: "4. Pengiriman & Bukti", icon: Truck },
  { key: "inspection", label: "5. Pemeriksaan Sistem", icon: CheckSquare },
  { key: "documents", label: "6. Dokumen & Generator", icon: Archive },
  { key: "audit", label: "7. Riwayat & Audit", icon: History },
];

export default function PackageWorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const packageId = params.id as string;

  const initialTab = searchParams.get("tab") || "identity";
  const [activeTab, setActiveTab] = useState<string>(initialTab);

  const [currentRole, setCurrentRole] = useState<UserRole>("ADMINISTRATION");
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Dirty uncommitted state retained across tabs
  const [dirtyLines, setDirtyLines] = useState<RevisionLine[] | null>(null);
  const [dirtyIdentity, setDirtyIdentity] = useState<any | null>(null);
  const [dirtyDates, setDirtyDates] = useState<any | null>(null);
  const [dirtyLogistics, setDirtyLogistics] = useState<any | null>(null);
  const [dirtyLogisticsLines, setDirtyLogisticsLines] = useState<RevisionLine[] | null>(null);

  // Modals
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);
  const [isConflictOpen, setIsConflictOpen] = useState(false);
  const [isReopenOpen, setIsReopenOpen] = useState(false);
  const [isCancelOpen, setIsCancelOpen] = useState(false);
  const [conflictServerVersion, setConflictServerVersion] = useState<number>(1);

  // Dispute & Blocking error status
  const [hasLogisticsDispute, setHasLogisticsDispute] = useState(false);

  const canEditPackageContent =
    currentRole === "ADMINISTRATION" || currentRole === "SYSTEM_ADMINISTRATOR";
  const canEditLogistics =
    currentRole === "LOGISTICS" ||
    currentRole === "ADMINISTRATION" ||
    currentRole === "SYSTEM_ADMINISTRATOR";
  const canViewInspectionAndDocs = currentRole !== "LOGISTICS";

  useEffect(() => {
    const syncRole = () => setCurrentRole(getCurrentRole());
    syncRole();
    window.addEventListener("pci_role_changed", syncRole);
    window.addEventListener("pci_auth_changed", syncRole);
    return () => {
      window.removeEventListener("pci_role_changed", syncRole);
      window.removeEventListener("pci_auth_changed", syncRole);
    };
  }, []);

  useEffect(() => {
    if (!canViewInspectionAndDocs && (activeTab === "inspection" || activeTab === "documents")) {
      setActiveTab("logistics");
      router.replace(`/packages/${packageId}?tab=logistics`, { scroll: false });
    }
  }, [canViewInspectionAndDocs, activeTab, packageId, router]);

  // Fetch package
  const {
    data: packageData,
    isLoading: isPkgLoading,
    error: pkgError,
    refetch: refetchPackage,
  } = useQuery<PackageItem>({
    queryKey: ["package", packageId],
    queryFn: () => apiClient.getPackage(packageId),
  });

  // Active revision
  const revisions = packageData?.revisions || [];
  const latestRevision = revisions.length > 0 ? revisions[revisions.length - 1] : null;

  // Validation run query (skipped for LOGISTICS per RBAC)
  const { data: validationRun, refetch: refetchValidation } = useQuery<ValidationRun | null>({
    queryKey: ["validation", latestRevision?.id],
    queryFn: () => (latestRevision ? apiClient.validateRevision(latestRevision.id) : null),
    enabled: Boolean(latestRevision?.id) && canViewInspectionAndDocs,
  });

  const isLocked = Boolean(latestRevision?.is_locked);
  const isTabs1to3ReadOnly = isLocked || !canEditPackageContent;
  const isLogisticsReadOnly = isLocked || !canEditLogistics;

  const visibleTabs = TABS.filter(
    (tab) => canViewInspectionAndDocs || (tab.key !== "inspection" && tab.key !== "documents")
  );

  const handleTabChange = (key: string) => {
    if (!canViewInspectionAndDocs && (key === "inspection" || key === "documents")) {
      return;
    }
    setActiveTab(key);
    router.replace(`/packages/${packageId}?tab=${key}`, { scroll: false });
  };

  // Save changes handler
  const handleSave = async () => {
    if (!latestRevision || !isDirty) return;
    setIsSaving(true);
    try {
      let currentVersion = latestRevision.version;
      if (canEditPackageContent && dirtyLines) {
        const updated = await apiClient.updateRevisionLines(
          latestRevision.id,
          dirtyLines,
          currentVersion
        );
        currentVersion = updated.version;
      }
      if (canEditPackageContent && dirtyIdentity) {
        const updated = await apiClient.updateRevisionDetails(
          latestRevision.id,
          {
            expected_version: currentVersion,
            school_snapshot: dirtyIdentity.school_snapshot,
            company_snapshot: dirtyIdentity.company_snapshot,
            officials_snapshot: dirtyIdentity.officials_snapshot,
            tax_policy_snapshot: dirtyIdentity.tax_policy_snapshot,
          }
        );
        currentVersion = updated.version;
      }
      if (canEditPackageContent && dirtyDates) {
        const updated = await apiClient.updateRevisionDetails(
          latestRevision.id,
          {
            expected_version: currentVersion,
            events: dirtyDates.events,
            numbers: dirtyDates.numbers,
          }
        );
        currentVersion = updated.version;
      }
      if (canEditLogistics && (dirtyLogistics || dirtyLogisticsLines)) {
        const baseLogistics = dirtyLogistics || {};
        const payload: any = {
          ...baseLogistics,
          dispatch_date: baseLogistics.dispatch_date || null,
          receipt_date: baseLogistics.receipt_date || baseLogistics.actual_delivery_date || null,
          actual_delivery_date: baseLogistics.receipt_date || baseLogistics.actual_delivery_date || null,
        };
        if (dirtyLogisticsLines) {
          payload.line_updates = dirtyLogisticsLines.map((l) => ({
            line_number: l.line_number,
            condition: l.condition || "BAIK",
            received_quantity:
              l.received_quantity !== undefined && l.received_quantity !== null
                ? Number(l.received_quantity)
                : Number(l.quantity),
          }));
        }
        await apiClient.updateLogistics(latestRevision.id, payload);
      }

      setIsDirty(false);
      setDirtyLines(null);
      setDirtyIdentity(null);
      setDirtyDates(null);
      setDirtyLogistics(null);
      setDirtyLogisticsLines(null);
      await refetchPackage();
      if (canViewInspectionAndDocs) {
        await refetchValidation();
      }
      return currentVersion;
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 409) {
        setConflictServerVersion(latestRevision.version + 1);
        setIsConflictOpen(true);
      } else {
        alert(`Gagal menyimpan perubahan: ${err.message || err}`);
      }
      return null;
    } finally {
      setIsSaving(false);
    }
  };

  const handleRefreshAll = async () => {
    await refetchPackage();
    if (canViewInspectionAndDocs) {
      await refetchValidation();
    }
  };

  if (isPkgLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-screen font-mono text-xs text-muted-foreground gap-2">
        <Loader2 className="w-5 h-5 animate-spin text-primary" />
        <span>Memuat ruang kerja transaksi...</span>
      </div>
    );
  }

  if (pkgError || !packageData || !latestRevision) {
    return (
      <div className="flex flex-col items-center justify-center h-screen text-xs gap-3 p-4 text-center">
        <AlertCircle className="w-8 h-8 text-destructive" />
        <h2 className="font-semibold text-foreground text-sm">Paket Pengadaan Tidak Ditemukan</h2>
        <p className="text-muted-foreground max-w-sm">
          {(pkgError as any)?.message || "ID paket pengadaan tidak valid atau belum memiliki revisi aktif."}
        </p>
        <button
          type="button"
          onClick={() => router.push("/packages")}
          className="px-3 py-1.5 text-xs bg-muted hover:bg-muted/80 rounded text-foreground font-medium"
        >
          Kembali ke Daftar Paket
        </button>
      </div>
    );
  }

  const blockingErrorsCount = validationRun?.findings?.filter((f) => f.severity === "BLOCK").length || 0;

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background">
      {/* 1. Persistent Transaction Header */}
      <WorkspaceHeader
        packageData={packageData}
        revision={latestRevision}
        currentRole={currentRole}
        isDirty={isDirty}
        isSaving={isSaving}
        onSave={handleSave}
        onRefresh={handleRefreshAll}
        onOpenApproval={() => setIsApprovalOpen(true)}
        onOpenRejection={() => setIsApprovalOpen(true)}
        onOpenReopen={() => setIsReopenOpen(true)}
        onOpenCancel={() => setIsCancelOpen(true)}
        onSwitchTab={handleTabChange}
        hasLogisticsDispute={hasLogisticsDispute}
        blockingErrorsCount={blockingErrorsCount}
      />

      {/* 2. Horizontal Tab Navigation Strip */}
      <div className="border-b border-border bg-card px-4 flex items-center gap-1 overflow-x-auto select-none shadow-sm">
        {visibleTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;

          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => handleTabChange(tab.key)}
              className={`flex items-center gap-2 px-3.5 py-2.5 text-xs border-b-2 transition-all whitespace-nowrap ${
                isActive
                  ? "border-primary text-primary font-bold bg-primary/10"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:bg-muted/50 font-medium"
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? "text-primary" : "text-muted-foreground"}`} />
              <span>{tab.label}</span>
              {tab.key === "inspection" && blockingErrorsCount > 0 && (
                <span className="ml-1 px-1.5 py-0.2 rounded bg-red-500/20 text-red-700 dark:text-red-300 font-mono text-[9px] border border-red-500/40 font-bold">
                  {blockingErrorsCount}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* 3. Tab Workspace Content (Scrollable) */}
      <div className="flex-1 overflow-y-auto bg-background">
        {activeTab === "identity" && (
          <TabIdentity
            revision={latestRevision}
            isReadOnly={isTabs1to3ReadOnly}
            onIdentityChanged={(payload) => {
              setDirtyIdentity(payload);
              setIsDirty(true);
            }}
          />
        )}

        {activeTab === "items" && (
          <TabItems
            revision={latestRevision}
            isReadOnly={isTabs1to3ReadOnly}
            onLinesChanged={(newLines) => {
              setDirtyLines(newLines);
              setIsDirty(true);
            }}
          />
        )}

        {activeTab === "dates" && (
          <TabDatesNumbers
            revision={latestRevision}
            isReadOnly={isTabs1to3ReadOnly}
            onDataChanged={(payload) => {
              setDirtyDates(payload);
              setIsDirty(true);
            }}
          />
        )}

        {activeTab === "logistics" && (
          <TabLogistics
            revision={latestRevision}
            currentRole={currentRole}
            isReadOnly={isLogisticsReadOnly}
            onLogisticsDisputeStatusChanged={setHasLogisticsDispute}
            onLinesChanged={(newLines) => {
              setDirtyLogisticsLines(newLines);
              setIsDirty(true);
            }}
            onLogisticsChanged={(newLogistics) => {
              setDirtyLogistics(newLogistics);
              setIsDirty(true);
            }}
          />
        )}

        {activeTab === "inspection" && canViewInspectionAndDocs && (
          <TabInspection
            revision={latestRevision}
            validationRun={validationRun}
            currentRole={currentRole}
            isReadOnly={isTabs1to3ReadOnly}
            onRefresh={handleRefreshAll}
            onClearDirty={() => {
              setIsDirty(false);
              setDirtyLines(null);
              setDirtyIdentity(null);
              setDirtyDates(null);
              setDirtyLogistics(null);
              setDirtyLogisticsLines(null);
            }}
            onNavigateToField={(tabKey) => handleTabChange(tabKey)}
          />
        )}

        {activeTab === "documents" && canViewInspectionAndDocs && (
          <TabDocuments
            revision={latestRevision}
            packageData={packageData}
            currentRole={currentRole}
            isReadOnly={isTabs1to3ReadOnly}
          />
        )}

        {activeTab === "audit" && (
          <TabAudit packageId={packageData.id} revision={latestRevision} currentRole={currentRole} />
        )}
      </div>

      {/* 4. Modals */}
      {/* Finance Director Approval Modal */}
      <ApprovalModal
        isOpen={isApprovalOpen}
        revision={latestRevision}
        onSuccess={handleRefreshAll}
        onClose={() => setIsApprovalOpen(false)}
      />

      {/* Reopen Revision Modal */}
      <ReopenModal
        isOpen={isReopenOpen}
        packageCode={packageData.package_code || packageData.package_number || "PKG"}
        currentRevisionNumber={latestRevision.revision_number}
        onConfirm={async (reason) => {
          await apiClient.reopenPackage(packageData.id, reason);
          await handleRefreshAll();
        }}
        onClose={() => setIsReopenOpen(false)}
      />

      {/* Cancel Package Modal */}
      <CancelModal
        isOpen={isCancelOpen}
        packageCode={packageData.package_code || packageData.package_number || "PKG"}
        onConfirm={async (reason) => {
          await apiClient.cancelPackage(packageData.id, reason, latestRevision.version);
          await handleRefreshAll();
        }}
        onClose={() => setIsCancelOpen(false)}
      />


      {/* HTTP 409 Concurrency Conflict Reconciliation Dialog */}
      <ConflictModal
        isOpen={isConflictOpen}
        packageId={packageData.id}
        serverVersion={conflictServerVersion}
        localVersion={latestRevision.version}
        onReloadServer={async () => {
          setIsDirty(false);
          setDirtyLines(null);
          setDirtyIdentity(null);
          setDirtyDates(null);
          await handleRefreshAll();
        }}
        onSaveAsNewRevision={async () => {
          await apiClient.reopenPackage(
            packageData.id,
            "Revisi baru dibuat untuk rekonsiliasi konflik penyuntingan bersamaan."
          );
          await handleRefreshAll();
        }}
        onClose={() => setIsConflictOpen(false)}
      />
    </div>
  );
}

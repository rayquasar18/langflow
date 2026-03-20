import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  useGetTenantDetailStats,
  useGetTenantFlows,
  usePatchTenant,
  useReactivateTenant,
  useSuspendTenant,
} from "@/controllers/API/queries/admin";
import { useCustomNavigate } from "@/customization/hooks/use-custom-navigate";
import getWidgetCode from "@/modals/apiModal/utils/get-widget-code";
import useAlertStore from "@/stores/alertStore";
import type { TenantFlowRead } from "@/types/admin";
import IconComponent from "../../../components/common/genericIconComponent";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../../components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../../components/ui/dialog";
import { Input } from "../../../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../../components/ui/select";
import { Skeleton } from "../../../components/ui/skeleton";

type ConfirmDialogState =
  | { type: "tier"; newTier: string }
  | { type: "suspend" }
  | { type: "reactivate" }
  | null;

export default function TenantDetailPage() {
  const { tenantId } = useParams<{ tenantId: string }>();
  const navigate = useCustomNavigate();
  const setSuccessData = useAlertStore((state) => state.setSuccessData);
  const setErrorData = useAlertStore((state) => state.setErrorData);

  const { data: tenant, isLoading } = useGetTenantDetailStats({
    tenantId: tenantId ?? "",
  });
  const { data: flows } = useGetTenantFlows({ tenantId: tenantId ?? "" });
  const { mutate: patchTenant, isPending: isPatchPending } = usePatchTenant();
  const { mutate: suspendTenant, isPending: isSuspendPending } =
    useSuspendTenant();
  const { mutate: reactivateTenant, isPending: isReactivatePending } =
    useReactivateTenant();

  // Quota form state
  const [maxFlows, setMaxFlows] = useState<string>("");
  const [maxKbDocs, setMaxKbDocs] = useState<string>("");
  const [maxRequestsPerMin, setMaxRequestsPerMin] = useState<string>("");
  const [formDirty, setFormDirty] = useState(false);

  // Confirmation dialog
  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState>(null);

  // Embed code dialog
  const [embedFlow, setEmbedFlow] = useState<TenantFlowRead | null>(null);

  // Sync quota form from tenant data
  useEffect(() => {
    if (tenant) {
      setFormDirty(false);
    }
  }, [tenant]);

  const handleQuotaChange = useCallback(
    (setter: React.Dispatch<React.SetStateAction<string>>) =>
      (e: React.ChangeEvent<HTMLInputElement>) => {
        setter(e.target.value);
        setFormDirty(true);
      },
    [],
  );

  const handleSaveQuotas = useCallback(() => {
    if (!tenantId) return;
    patchTenant(
      {
        tenantId,
        data: {
          max_flows: maxFlows === "" ? null : Number(maxFlows),
          max_kb_docs: maxKbDocs === "" ? null : Number(maxKbDocs),
          max_requests_per_min:
            maxRequestsPerMin === "" ? null : Number(maxRequestsPerMin),
        },
      },
      {
        onSuccess: () => {
          setSuccessData({ title: "Changes saved" });
          setFormDirty(false);
        },
        onError: () => {
          setErrorData({
            title:
              "Failed to save changes. Please try again or refresh the page.",
          });
        },
      },
    );
  }, [
    tenantId,
    maxFlows,
    maxKbDocs,
    maxRequestsPerMin,
    patchTenant,
    setSuccessData,
    setErrorData,
  ]);

  const handleConfirmAction = useCallback(() => {
    if (!tenantId || !confirmDialog) return;

    if (confirmDialog.type === "tier") {
      patchTenant(
        { tenantId, data: { tier: confirmDialog.newTier } },
        {
          onSuccess: () => {
            setSuccessData({ title: "Changes saved" });
          },
          onError: () => {
            setErrorData({
              title:
                "Failed to save changes. Please try again or refresh the page.",
            });
          },
        },
      );
    } else if (confirmDialog.type === "suspend") {
      suspendTenant(
        { tenantId },
        {
          onSuccess: () => {
            setSuccessData({ title: "Tenant suspended" });
          },
          onError: () => {
            setErrorData({
              title: "Failed to suspend tenant. Please try again.",
            });
          },
        },
      );
    } else if (confirmDialog.type === "reactivate") {
      reactivateTenant(
        { tenantId },
        {
          onSuccess: () => {
            setSuccessData({ title: "Tenant reactivated" });
          },
          onError: () => {
            setErrorData({
              title: "Failed to reactivate tenant. Please try again.",
            });
          },
        },
      );
    }
    setConfirmDialog(null);
  }, [
    tenantId,
    confirmDialog,
    patchTenant,
    suspendTenant,
    reactivateTenant,
    setSuccessData,
    setErrorData,
  ]);

  const tierBadgeVariant = useMemo(() => {
    switch (tenant?.tier?.toLowerCase()) {
      case "free":
        return "emerald" as const;
      case "pro":
        return "purpleStatic" as const;
      case "enterprise":
        return "pinkStatic" as const;
      default:
        return "secondaryStatic" as const;
    }
  }, [tenant?.tier]);

  const confirmDialogContent = useMemo(() => {
    if (!confirmDialog || !tenant) return null;
    switch (confirmDialog.type) {
      case "tier":
        return {
          title: "Change Tier",
          body: `Changing "${tenant.tenant_name}" from ${tenant.tier} to ${confirmDialog.newTier} will update quota limits immediately. Existing usage above new limits will not be deleted but new creation will be blocked.`,
          confirm: "Change Tier",
          variant: "default" as const,
        };
      case "suspend":
        return {
          title: "Suspend Tenant",
          body: `Suspending "${tenant.tenant_name}" will immediately block all users in this tenant from accessing the platform. Active sessions will be terminated. Are you sure?`,
          confirm: "Suspend Tenant",
          variant: "destructive" as const,
        };
      case "reactivate":
        return {
          title: "Reactivate Tenant",
          body: `Reactivating "${tenant.tenant_name}" will restore access for all users in this tenant.`,
          confirm: "Reactivate",
          variant: "default" as const,
        };
      default:
        return null;
    }
  }, [confirmDialog, tenant]);

  const embedCode = useMemo(() => {
    if (!embedFlow) return "";
    return getWidgetCode({
      flowId: embedFlow.id,
      flowName: embedFlow.name,
      webhookAuthEnable: false,
      isAuth: false,
    });
  }, [embedFlow]);

  const handleCopyEmbed = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(embedCode);
      setSuccessData({ title: "Embed code copied to clipboard" });
    } catch {
      setErrorData({ title: "Failed to copy to clipboard" });
    }
  }, [embedCode, setSuccessData, setErrorData]);

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6 p-4">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-3 gap-4">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
        <Skeleton className="h-32" />
      </div>
    );
  }

  if (!tenant) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-12">
        <h3 className="text-lg font-semibold">Tenant not found</h3>
        <Button variant="outline" onClick={() => navigate("/admin/tenants")}>
          Back to Tenants
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8 overflow-y-auto pb-8">
      {/* Back button + header */}
      <div>
        <Button
          variant="ghost"
          className="mb-2 gap-1 px-2 text-muted-foreground hover:text-foreground"
          onClick={() => navigate("/admin/tenants")}
        >
          <IconComponent name="ChevronLeft" className="h-4 w-4" />
          Back to Tenants
        </Button>
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold">{tenant.tenant_name}</h1>
          <Badge
            variant={tenant.is_active ? "successStatic" : "errorStatic"}
            size="sq"
          >
            {tenant.is_active ? "Active" : "Suspended"}
          </Badge>
          <Badge variant={tierBadgeVariant} size="sq">
            {tenant.tier}
          </Badge>
        </div>
      </div>

      {/* Usage stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-normal uppercase text-muted-foreground">
              Flows
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p
              className="text-3xl font-semibold"
              aria-label={`${tenant.flow_count} flows`}
            >
              {tenant.flow_count}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-normal uppercase text-muted-foreground">
              KB Documents
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p
              className="text-3xl font-semibold"
              aria-label={`${tenant.kb_doc_count} KB documents`}
            >
              {tenant.kb_doc_count}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-normal uppercase text-muted-foreground">
              Requests
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p
              className="text-3xl font-semibold"
              aria-label={`${tenant.request_count} requests`}
            >
              {tenant.request_count}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tier management */}
      <div className="rounded-lg border p-6">
        <h2 className="mb-4 text-lg font-semibold">Tier</h2>
        <div className="flex items-center gap-4">
          <Select
            value={tenant.tier}
            onValueChange={(newTier) => {
              if (newTier !== tenant.tier) {
                setConfirmDialog({ type: "tier", newTier });
              }
            }}
          >
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Select tier" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Free">Free</SelectItem>
              <SelectItem value="Pro">Pro</SelectItem>
              <SelectItem value="Enterprise">Enterprise</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Quota overrides */}
      <div className="rounded-lg border p-6">
        <h2 className="mb-4 text-lg font-semibold">Quota Overrides</h2>
        <p className="mb-4 text-sm text-muted-foreground">
          Leave empty to use tier defaults.
        </p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <label className="mb-1 block text-sm text-muted-foreground">
              Max Flows
            </label>
            <Input
              type="number"
              min={0}
              placeholder="Tier default"
              value={maxFlows}
              onChange={handleQuotaChange(setMaxFlows)}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted-foreground">
              Max KB Docs
            </label>
            <Input
              type="number"
              min={0}
              placeholder="Tier default"
              value={maxKbDocs}
              onChange={handleQuotaChange(setMaxKbDocs)}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted-foreground">
              Max Requests/min
            </label>
            <Input
              type="number"
              min={0}
              placeholder="Tier default"
              value={maxRequestsPerMin}
              onChange={handleQuotaChange(setMaxRequestsPerMin)}
            />
          </div>
        </div>
        <div className="mt-4">
          <Button
            disabled={!formDirty || isPatchPending}
            onClick={handleSaveQuotas}
          >
            {isPatchPending ? "Saving..." : "Save Changes"}
          </Button>
        </div>
      </div>

      {/* Status management */}
      <div className="rounded-lg border p-6">
        <h2 className="mb-4 text-lg font-semibold">Tenant Status</h2>
        {tenant.is_active ? (
          <Button
            variant="destructive"
            disabled={isSuspendPending}
            onClick={() => setConfirmDialog({ type: "suspend" })}
          >
            {isSuspendPending ? "Suspending..." : "Suspend Tenant"}
          </Button>
        ) : (
          <Button
            variant="outline"
            disabled={isReactivatePending}
            onClick={() => setConfirmDialog({ type: "reactivate" })}
          >
            {isReactivatePending ? "Reactivating..." : "Reactivate Tenant"}
          </Button>
        )}
      </div>

      {/* Deployed flows + embed codes */}
      <div className="rounded-lg border p-6">
        <h2 className="mb-4 text-lg font-semibold">Deployed Flows</h2>
        {!flows || flows.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No deployed flows for this tenant.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {flows
              .filter((f) => !f.is_component)
              .map((flow) => (
                <div
                  key={flow.id}
                  className="flex items-center justify-between rounded-md border px-4 py-3"
                >
                  <div>
                    <p className="font-medium">{flow.name}</p>
                    <p className="text-xs text-muted-foreground">
                      Updated: {new Date(flow.updated_at).toLocaleDateString()}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setEmbedFlow(flow)}
                  >
                    Get Embed Code
                  </Button>
                </div>
              ))}
          </div>
        )}
      </div>

      {/* Confirmation dialog */}
      <Dialog
        open={confirmDialog !== null}
        onOpenChange={(open) => {
          if (!open) setConfirmDialog(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{confirmDialogContent?.title}</DialogTitle>
            <DialogDescription>{confirmDialogContent?.body}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmDialog(null)}>
              Cancel
            </Button>
            <Button
              variant={confirmDialogContent?.variant}
              onClick={handleConfirmAction}
            >
              {confirmDialogContent?.confirm}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Embed code dialog */}
      <Dialog
        open={embedFlow !== null}
        onOpenChange={(open) => {
          if (!open) setEmbedFlow(null);
        }}
      >
        <DialogContent className="max-w-[560px]">
          <DialogHeader>
            <DialogTitle>Embed Chat Widget</DialogTitle>
            <DialogDescription>
              Add this snippet to any webpage to embed a chat widget for this
              flow.
            </DialogDescription>
          </DialogHeader>
          <pre className="overflow-x-auto rounded-md bg-muted p-4 font-mono text-sm">
            {embedCode}
          </pre>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEmbedFlow(null)}>
              Close
            </Button>
            <Button onClick={handleCopyEmbed}>Copy Code</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

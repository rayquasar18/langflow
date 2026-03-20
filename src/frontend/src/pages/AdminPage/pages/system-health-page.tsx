import { useCallback } from "react";
import { useGetSystemHealth } from "@/controllers/API/queries/admin";
import type { ServiceHealthRead } from "@/types/admin";
import IconComponent from "../../../components/common/genericIconComponent";
import { Button } from "../../../components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../../components/ui/card";
import { Skeleton } from "../../../components/ui/skeleton";

const STATUS_CONFIG: Record<
  ServiceHealthRead["status"],
  { color: string; label: string }
> = {
  healthy: { color: "bg-green-500", label: "Healthy" },
  degraded: { color: "bg-yellow-500", label: "Degraded" },
  unreachable: { color: "bg-red-500", label: "Unreachable" },
  unknown: { color: "bg-gray-400", label: "Unknown" },
};

export default function SystemHealthPage() {
  const { data, isLoading, isError, refetch, isFetching } =
    useGetSystemHealth();

  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  const formatTimestamp = useCallback((iso: string) => {
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  }, []);

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
        <h3 className="text-lg font-semibold">Unable to check services</h3>
        <p className="text-sm text-muted-foreground">
          Could not reach the health aggregation endpoint. Verify the Auth
          Service is running.
        </p>
        <Button variant="outline" className="mt-4" onClick={handleRefresh}>
          <IconComponent name="RefreshCw" className="mr-2 h-4 w-4" />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-6">
      {/* Header with refresh */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">System Health</h2>
        <Button variant="outline" disabled={isFetching} onClick={handleRefresh}>
          <IconComponent
            name="RefreshCw"
            className={`mr-2 h-4 w-4 ${isFetching ? "animate-spin" : ""}`}
          />
          {isFetching ? "Refreshing..." : "Refresh"}
        </Button>
      </div>

      {/* Service cards grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-lg" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {data?.services.map((service) => {
            const config =
              STATUS_CONFIG[service.status] ?? STATUS_CONFIG.unknown;
            return (
              <Card key={service.name} className="border">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <span
                      className={`inline-block h-2 w-2 rounded-full ${config.color}`}
                      aria-label={`Service status: ${config.label}`}
                    />
                    {service.name}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4">
                    <span className="text-sm font-medium">{config.label}</span>
                    {service.response_time_ms !== null && (
                      <span className="text-sm text-muted-foreground">
                        {service.response_time_ms}ms
                      </span>
                    )}
                  </div>
                  {service.detail && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      {service.detail}
                    </p>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Last checked */}
      {data?.checked_at && (
        <p className="text-sm text-muted-foreground">
          Last checked: {formatTimestamp(data.checked_at)}
        </p>
      )}
    </div>
  );
}

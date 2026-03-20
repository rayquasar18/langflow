import { useCallback, useMemo, useState } from "react";
import PaginatorComponent from "@/components/common/paginatorComponent";
import { useGetTenantStats } from "@/controllers/API/queries/admin";
import { useCustomNavigate } from "@/customization/hooks/use-custom-navigate";
import type { TenantStatsRead } from "@/types/admin";
import IconComponent from "../../../components/common/genericIconComponent";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../../components/ui/card";
import { Input } from "../../../components/ui/input";
import { Skeleton } from "../../../components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../../components/ui/table";
import {
  PAGINATION_PAGE,
  PAGINATION_ROWS_COUNT,
  PAGINATION_SIZE,
} from "../../../constants/constants";

function getTierBadgeVariant(tier: string) {
  switch (tier.toLowerCase()) {
    case "free":
      return "emerald" as const;
    case "pro":
      return "purpleStatic" as const;
    case "enterprise":
      return "pinkStatic" as const;
    default:
      return "secondaryStatic" as const;
  }
}

function getStatusBadgeVariant(isActive: boolean) {
  return isActive ? ("successStatic" as const) : ("errorStatic" as const);
}

export default function TenantListPage() {
  const navigate = useCustomNavigate();
  const { data: tenants, isLoading, isError } = useGetTenantStats();

  const [searchInput, setSearchInput] = useState("");
  const [pageIndex, setPageIndex] = useState(PAGINATION_PAGE);
  const [pageSize, setPageSize] = useState(PAGINATION_SIZE);

  const filteredTenants = useMemo(() => {
    if (!tenants) return [];
    if (!searchInput) return tenants;
    return tenants.filter((t) =>
      t.tenant_name.toLowerCase().includes(searchInput.toLowerCase()),
    );
  }, [tenants, searchInput]);

  const paginatedTenants = useMemo(() => {
    const start = pageSize * (pageIndex - 1);
    return filteredTenants.slice(start, start + pageSize);
  }, [filteredTenants, pageIndex, pageSize]);

  const handlePaginate = useCallback((newIndex: number, newSize: number) => {
    setPageIndex(newIndex);
    setPageSize(newSize);
  }, []);

  const totalTenants = tenants?.length ?? 0;
  const activeTenants = tenants?.filter((t) => t.is_active).length ?? 0;
  const suspendedTenants = totalTenants - activeTenants;

  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setSearchInput(e.target.value);
      setPageIndex(PAGINATION_PAGE);
    },
    [],
  );

  return (
    <div className="flex h-full flex-col gap-6">
      {/* Summary stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-normal uppercase text-muted-foreground">
              Total Tenants
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p
              className="text-3xl font-semibold"
              aria-label={`${totalTenants} total tenants`}
            >
              {isLoading ? <Skeleton className="h-8 w-16" /> : totalTenants}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-normal uppercase text-muted-foreground">
              Active
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p
              className="text-3xl font-semibold"
              aria-label={`${activeTenants} active tenants`}
            >
              {isLoading ? <Skeleton className="h-8 w-16" /> : activeTenants}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-normal uppercase text-muted-foreground">
              Suspended
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p
              className="text-3xl font-semibold"
              aria-label={`${suspendedTenants} suspended tenants`}
            >
              {isLoading ? <Skeleton className="h-8 w-16" /> : suspendedTenants}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <div className="flex items-center gap-4">
        <div className="flex w-96 items-center gap-2">
          <Input
            placeholder="Search tenants..."
            value={searchInput}
            onChange={handleSearchChange}
          />
          {searchInput.length > 0 ? (
            <div
              className="cursor-pointer"
              onClick={() => {
                setSearchInput("");
                setPageIndex(PAGINATION_PAGE);
              }}
            >
              <IconComponent name="X" className="w-5 text-foreground" />
            </div>
          ) : (
            <div>
              <IconComponent name="Search" className="w-5 text-foreground" />
            </div>
          )}
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-md" />
          ))}
        </div>
      ) : isError ? (
        <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
          <h3 className="text-lg font-semibold">
            Failed to load usage statistics
          </h3>
          <p className="text-sm text-muted-foreground">Refresh to retry.</p>
        </div>
      ) : filteredTenants.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
          <h3 className="text-lg font-semibold">No tenants yet</h3>
          <p className="text-sm text-muted-foreground">
            Tenants will appear here once created. Use the Auth Service API to
            create your first tenant.
          </p>
        </div>
      ) : (
        <div className="flex flex-1 flex-col">
          <div className="flex-1 overflow-auto rounded-md border bg-background">
            <Table>
              <TableHeader className="bg-muted">
                <TableRow>
                  <TableHead className="h-10">Name</TableHead>
                  <TableHead className="h-10">Tier</TableHead>
                  <TableHead className="h-10">Status</TableHead>
                  <TableHead className="h-10">Flows</TableHead>
                  <TableHead className="h-10">KB Docs</TableHead>
                  <TableHead className="h-10">Requests</TableHead>
                  <TableHead className="h-10 w-[80px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedTenants.map((tenant: TenantStatsRead) => (
                  <TableRow
                    key={tenant.tenant_id}
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() =>
                      navigate(`/admin/tenants/${tenant.tenant_id}`)
                    }
                  >
                    <TableCell className="py-3 font-medium">
                      {tenant.tenant_name}
                    </TableCell>
                    <TableCell className="py-3">
                      <Badge
                        variant={getTierBadgeVariant(tenant.tier)}
                        size="sq"
                      >
                        {tenant.tier}
                      </Badge>
                    </TableCell>
                    <TableCell className="py-3">
                      <Badge
                        variant={getStatusBadgeVariant(tenant.is_active)}
                        size="sq"
                      >
                        {tenant.is_active ? "Active" : "Suspended"}
                      </Badge>
                    </TableCell>
                    <TableCell className="py-3">{tenant.flow_count}</TableCell>
                    <TableCell className="py-3">
                      {tenant.kb_doc_count}
                    </TableCell>
                    <TableCell className="py-3">
                      {tenant.request_count}
                    </TableCell>
                    <TableCell className="py-3">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/admin/tenants/${tenant.tenant_id}`);
                        }}
                        aria-label="View tenant details"
                      >
                        <IconComponent
                          name="ChevronRight"
                          className="h-4 w-4"
                        />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <div className="mt-4">
            <PaginatorComponent
              pageIndex={pageIndex}
              pageSize={pageSize}
              totalRowsCount={filteredTenants.length}
              paginate={handlePaginate}
              rowsCount={PAGINATION_ROWS_COUNT}
            />
          </div>
        </div>
      )}
    </div>
  );
}

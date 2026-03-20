import type { TenantStatsRead } from "@/types/admin";
import type { useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { UseRequestProcessor } from "../../services/request-processor";

interface GetTenantDetailStatsParams {
  tenantId: string;
}

export const useGetTenantDetailStats: useQueryFunctionType<
  GetTenantDetailStatsParams,
  TenantStatsRead
> = (params, options?) => {
  const { query } = UseRequestProcessor();

  async function getTenantDetailStatsFn() {
    const response = await api.get<TenantStatsRead>(
      `/api/v1/admin/stats/${params.tenantId}`,
    );
    return response.data;
  }

  const queryResult = query(
    ["useGetTenantDetailStats", params.tenantId],
    getTenantDetailStatsFn,
    {
      enabled: !!params.tenantId,
      refetchOnWindowFocus: false,
      staleTime: 30000,
      ...options,
    },
  );

  return queryResult;
};

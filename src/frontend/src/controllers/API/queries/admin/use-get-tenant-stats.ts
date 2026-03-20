import type { TenantStatsRead } from "@/types/admin";
import type { useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { UseRequestProcessor } from "../../services/request-processor";

export const useGetTenantStats: useQueryFunctionType<
  undefined,
  TenantStatsRead[]
> = (options?) => {
  const { query } = UseRequestProcessor();

  async function getTenantStatsFn() {
    const response = await api.get<TenantStatsRead[]>("/api/v1/admin/stats");
    return response.data;
  }

  const queryResult = query(["useGetTenantStats"], getTenantStatsFn, {
    refetchOnWindowFocus: false,
    staleTime: 30000,
    ...options,
  });

  return queryResult;
};

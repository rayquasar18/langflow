import type { TenantFlowRead } from "@/types/admin";
import type { useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { UseRequestProcessor } from "../../services/request-processor";

interface GetTenantFlowsParams {
  tenantId: string;
}

export const useGetTenantFlows: useQueryFunctionType<
  GetTenantFlowsParams,
  TenantFlowRead[]
> = (params, options?) => {
  const { query } = UseRequestProcessor();

  async function getTenantFlowsFn() {
    const response = await api.get<TenantFlowRead[]>(
      `/api/v1/admin/tenants/${params.tenantId}/flows`,
    );
    return response.data;
  }

  const queryResult = query(
    ["useGetTenantFlows", params.tenantId],
    getTenantFlowsFn,
    {
      enabled: !!params.tenantId,
      refetchOnWindowFocus: false,
      ...options,
    },
  );

  return queryResult;
};

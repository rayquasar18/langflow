import type { useMutationFunctionType } from "@/types/api";
import { api } from "../../api";
import { UseRequestProcessor } from "../../services/request-processor";

interface SuspendTenantParams {
  tenantId: string;
}

export const useSuspendTenant: useMutationFunctionType<
  undefined,
  SuspendTenantParams
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  async function suspendTenantFn({
    tenantId,
  }: SuspendTenantParams): Promise<unknown> {
    const response = await api.post(
      `/api/v1/admin/tenants/${tenantId}/suspend`,
    );
    return response.data;
  }

  const mutation = mutate(["useSuspendTenant"], suspendTenantFn, {
    ...options,
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["useGetTenantDetailStats"],
      });
      queryClient.invalidateQueries({
        queryKey: ["useGetTenantStats"],
      });
    },
  });

  return mutation;
};

export const useReactivateTenant: useMutationFunctionType<
  undefined,
  SuspendTenantParams
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  async function reactivateTenantFn({
    tenantId,
  }: SuspendTenantParams): Promise<unknown> {
    const response = await api.post(
      `/api/v1/admin/tenants/${tenantId}/reactivate`,
    );
    return response.data;
  }

  const mutation = mutate(["useReactivateTenant"], reactivateTenantFn, {
    ...options,
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["useGetTenantDetailStats"],
      });
      queryClient.invalidateQueries({
        queryKey: ["useGetTenantStats"],
      });
    },
  });

  return mutation;
};

import type { TenantUpdate } from "@/types/admin";
import type { useMutationFunctionType } from "@/types/api";
import { api } from "../../api";
import { UseRequestProcessor } from "../../services/request-processor";

interface PatchTenantParams {
  tenantId: string;
  data: TenantUpdate;
}

export const usePatchTenant: useMutationFunctionType<
  undefined,
  PatchTenantParams
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  async function patchTenantFn({
    tenantId,
    data,
  }: PatchTenantParams): Promise<unknown> {
    const response = await api.patch(`/api/v1/admin/tenants/${tenantId}`, data);
    return response.data;
  }

  const mutation = mutate(["usePatchTenant"], patchTenantFn, {
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

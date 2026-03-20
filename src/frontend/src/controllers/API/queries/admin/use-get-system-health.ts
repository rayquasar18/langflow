import type { SystemHealthRead } from "@/types/admin";
import type { useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { UseRequestProcessor } from "../../services/request-processor";

export const useGetSystemHealth: useQueryFunctionType<
  undefined,
  SystemHealthRead
> = (options?) => {
  const { query } = UseRequestProcessor();

  async function getSystemHealthFn() {
    const response = await api.get<SystemHealthRead>("/api/v1/admin/health");
    return response.data;
  }

  const queryResult = query(["useGetSystemHealth"], getSystemHealthFn, {
    refetchInterval: 30000,
    refetchOnWindowFocus: true,
    ...options,
  });

  return queryResult;
};

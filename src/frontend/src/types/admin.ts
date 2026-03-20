export interface TenantStatsRead {
  tenant_id: string;
  tenant_name: string;
  tier: string;
  is_active: boolean;
  flow_count: number;
  kb_doc_count: number;
  request_count: number;
}

export interface ServiceHealthRead {
  name: string;
  status: "healthy" | "degraded" | "unreachable" | "unknown";
  response_time_ms: number | null;
  detail: string | null;
}

export interface SystemHealthRead {
  services: ServiceHealthRead[];
  checked_at: string;
}

export interface TenantUpdate {
  name?: string;
  tier?: string;
  is_active?: boolean;
  max_flows?: number | null;
  max_kb_docs?: number | null;
  max_requests_per_min?: number | null;
}

export interface TenantFlowRead {
  id: string;
  name: string;
  is_component: boolean;
  updated_at: string;
}

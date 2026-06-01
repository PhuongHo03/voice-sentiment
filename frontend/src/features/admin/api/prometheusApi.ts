import type { PrometheusQueryResponse } from '../types/metrics';

const prometheusBaseUrl = import.meta.env.VITE_PROMETHEUS_BASE_URL || '/observability/api';

export async function queryPrometheus(query: string): Promise<PrometheusQueryResponse> {
  const response = await fetch(`${prometheusBaseUrl}/v1/query?query=${encodeURIComponent(query)}`);
  const data = await response.json();

  if (!response.ok || data.status !== 'success') {
    throw new Error(data.error || 'Không thể truy vấn Prometheus');
  }

  return data;
}

export interface MetricCard {
  label: string;
  value: string;
  status?: 'ok' | 'warn' | 'error';
  detail?: string;
}

export interface ServiceHealthMetric {
  job: string;
  up: boolean;
  detail: string;
}

export interface PrometheusInstantValue {
  metric: Record<string, string>;
  value: [number, string];
}

export interface PrometheusQueryResponse {
  status: string;
  data?: {
    resultType: string;
    result: PrometheusInstantValue[];
  };
  error?: string;
}

export interface ObservabilityMetrics {
  serviceHealth: ServiceHealthMetric[];
  cards: MetricCard[];
  lastUpdated: string | null;
}

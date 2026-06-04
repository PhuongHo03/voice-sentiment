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

export interface SystemAlert {
  level: 'error' | 'warning';
  message: string;
}

export interface ObservabilityMetrics {
  serviceHealth: ServiceHealthMetric[];
  cards: MetricCard[];
  serviceMetrics: MetricCard[];
  alerts?: SystemAlert[];
  lastUpdated: string | null;
}

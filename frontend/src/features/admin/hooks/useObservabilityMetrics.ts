import { useCallback, useEffect, useState } from 'react';
import { queryPrometheus } from '../api/prometheusApi';
import type { MetricCard, ObservabilityMetrics, ServiceHealthMetric } from '../types/metrics';

const MONITORED_JOBS = ['backend', 'voice-worker', 'llm-worker', 'postgres', 'redis', 'rabbitmq', 'nginx'];

function parseNumber(value?: string): number {
  const parsed = Number(value ?? '0');
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatRate(value: number): string {
  return `${value.toFixed(2)}/s`;
}

function formatSeconds(value: number): string {
  if (value >= 1) return `${value.toFixed(2)}s`;
  return `${Math.round(value * 1000)}ms`;
}

export function useObservabilityMetrics(active: boolean) {
  const [metrics, setMetrics] = useState<ObservabilityMetrics>({ serviceHealth: [], cards: [], lastUpdated: null });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshMetrics = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [upData, requestRateData, errorRateData, latencyData, jobRateData] = await Promise.all([
        queryPrometheus('up{job=~"backend|voice-worker|llm-worker|postgres|redis|rabbitmq|nginx"}'),
        queryPrometheus('sum(rate(voice_sentiment_http_requests_total[5m]))'),
        queryPrometheus('sum(rate(voice_sentiment_http_requests_total{status=~"5.."}[5m]))'),
        queryPrometheus('histogram_quantile(0.95, sum(rate(voice_sentiment_http_request_duration_seconds_bucket[5m])) by (le))'),
        queryPrometheus('sum(rate(voice_sentiment_llm_jobs_total[5m]))'),
      ]);

      const upResults = upData.data?.result ?? [];
      const serviceHealth: ServiceHealthMetric[] = MONITORED_JOBS.map(job => {
        const item = upResults.find(result => result.metric.job === job);
        const isUp = item ? parseNumber(item.value[1]) === 1 : false;
        return {
          job,
          up: isUp,
          detail: item ? (isUp ? 'Đang scrape' : 'Mất scrape') : 'Chưa có target',
        };
      });

      const requestRate = parseNumber(requestRateData.data?.result?.[0]?.value?.[1]);
      const errorRate = parseNumber(errorRateData.data?.result?.[0]?.value?.[1]);
      const p95Latency = parseNumber(latencyData.data?.result?.[0]?.value?.[1]);
      const jobRate = parseNumber(jobRateData.data?.result?.[0]?.value?.[1]);
      const downCount = serviceHealth.filter(item => !item.up).length;

      const cards: MetricCard[] = [
        {
          label: 'Targets online',
          value: `${serviceHealth.length - downCount}/${serviceHealth.length}`,
          status: downCount === 0 ? 'ok' : 'error',
          detail: downCount === 0 ? 'Tất cả target đang được Prometheus scrape' : `${downCount} target đang down`,
        },
        {
          label: 'Request rate',
          value: formatRate(requestRate),
          status: 'ok',
          detail: 'Tổng HTTP request 5 phút gần nhất',
        },
        {
          label: '5xx rate',
          value: formatRate(errorRate),
          status: errorRate > 0 ? 'warn' : 'ok',
          detail: 'Tổng lỗi HTTP 5xx 5 phút gần nhất',
        },
        {
          label: 'P95 latency',
          value: formatSeconds(p95Latency),
          status: p95Latency > 2 ? 'warn' : 'ok',
          detail: 'P95 latency từ service HTTP metrics',
        },
        {
          label: 'LLM jobs',
          value: formatRate(jobRate),
          status: 'ok',
          detail: 'Tốc độ xử lý job worker 5 phút gần nhất',
        },
      ];

      setMetrics({ serviceHealth, cards, lastUpdated: new Date().toLocaleTimeString('vi-VN') });
    } catch (err: any) {
      setError(err.message || 'Không thể tải metrics');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!active) return;
    refreshMetrics();
    const interval = window.setInterval(refreshMetrics, 30000);
    return () => window.clearInterval(interval);
  }, [active, refreshMetrics]);

  return { metrics, isLoading, error, refreshMetrics };
}

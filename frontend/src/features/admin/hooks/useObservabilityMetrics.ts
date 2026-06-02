import { useCallback, useEffect, useState } from 'react';
import type { ObservabilityMetrics } from '../types/metrics';

export function useObservabilityMetrics(active: boolean) {
  const [metrics, setMetrics] = useState<ObservabilityMetrics>({ serviceHealth: [], cards: [], lastUpdated: null });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshMetrics = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/admin/metrics', { credentials: 'include' });
      if (!response.ok) {
        throw new Error(`Lỗi ${response.status}: Không thể tải metrics`);
      }
      const data: ObservabilityMetrics = await response.json();
      setMetrics(data);
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

import React from 'react';
import { useObservabilityMetrics } from '../hooks/useObservabilityMetrics';

interface AdminObservabilityDashboardProps {
  active: boolean;
}

export const AdminObservabilityDashboard: React.FC<AdminObservabilityDashboardProps> = ({ active }) => {
  const { metrics, isLoading, error, refreshMetrics } = useObservabilityMetrics(active);

  return (
    <section className="admin-observability">
      <div className="admin-section-header">
        <div>
          <h2>📈 Metrics hệ thống</h2>
          <p>Prometheus scrape metrics trực tiếp từ services/exporters. Frontend truy vấn qua Nginx, không qua backend.</p>
        </div>
        <button className="admin-inline-btn" onClick={refreshMetrics} disabled={isLoading}>
          {isLoading ? 'Đang tải...' : 'Làm mới'}
        </button>
      </div>

      <div className="observability-warning">
        ⚠️ Endpoint Prometheus qua Nginx hiện không có app-auth. Chỉ dùng an toàn trong môi trường local/dev hoặc sau khi thêm bảo vệ Nginx.
      </div>

      {error && <div className="admin-error-panel">{error}</div>}

      <div className="metrics-card-grid">
        {metrics.cards.map(card => (
          <article key={card.label} className={`metrics-card ${card.status ?? 'ok'}`}>
            <span className="metrics-card-label">{card.label}</span>
            <strong>{card.value}</strong>
            {card.detail && <small>{card.detail}</small>}
          </article>
        ))}
      </div>

      <div className="service-health-grid">
        {metrics.serviceHealth.map(item => (
          <article key={item.job} className={`service-health-card ${item.up ? 'up' : 'down'}`}>
            <span className="service-health-dot" />
            <div>
              <strong>{item.job}</strong>
              <small>{item.detail}</small>
            </div>
          </article>
        ))}
      </div>

      <div className="observability-footer">
        <span>Prometheus API: <code>/observability/api/v1/query</code></span>
        <span>Cập nhật lần cuối: {metrics.lastUpdated ?? 'Chưa có dữ liệu'}</span>
      </div>
    </section>
  );
};

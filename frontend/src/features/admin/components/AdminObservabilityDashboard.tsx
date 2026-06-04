import React from 'react';
import { useObservabilityMetrics } from '../hooks/useObservabilityMetrics';

interface AdminObservabilityDashboardProps {
  active: boolean;
}

export const AdminObservabilityDashboard: React.FC<AdminObservabilityDashboardProps> = ({ active }) => {
  const { metrics, isLoading, error, refreshMetrics } = useObservabilityMetrics(active);

  // Group metrics into Application & AI vs Infrastructure
  const appMetricLabels = ['Voice jobs', 'LLM jobs', 'Request rate', '5xx rate', 'API P95'];
  const appCards = metrics.cards.filter(c => appMetricLabels.includes(c.label));
  const infraCards = metrics.cards.filter(c => !appMetricLabels.includes(c.label));

  return (
    <main className="account-mgmt-layout admin-observability">
      {/* System Alert Banners */}
      {metrics.alerts && metrics.alerts.length > 0 && (
        <div className="observability-alerts-container">
          {metrics.alerts.map((alert, idx) => (
            <div key={idx} className={`system-alert-banner ${alert.level}`}>
              <span className="alert-icon">⚠️</span>
              <div className="alert-content">
                <strong>CẢNH BÁO HỆ THỐNG:</strong> {alert.message}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="observability-toolbar card">
        <div>
          <h2>📈 Observability Dashboard</h2>
          <span>Cập nhật lần cuối: {metrics.lastUpdated ?? 'Chưa có dữ liệu'}</span>
        </div>
        <button className="admin-inline-btn" onClick={refreshMetrics} disabled={isLoading}>
          {isLoading ? 'Đang tải...' : 'Làm mới'}
        </button>
      </div>

      {/* Service Health Grid */}
      <div className="card">
        <h3 className="metrics-section-title">🚦 Trạng thái dịch vụ (Service Health)</h3>
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
      </div>

      {error && <div className="admin-error-panel card">{error}</div>}

      {/* 🚀 Application & AI Metrics */}
      {appCards.length > 0 && (
        <div className="card">
          <h3 className="metrics-section-title">🚀 Application & AI Metrics</h3>
          <div className="metrics-card-grid">
            {appCards.map(card => (
              <article key={card.label} className={`metrics-card ${card.status ?? 'ok'}`}>
                <span className="metrics-card-label">{card.label}</span>
                <strong>{card.value}</strong>
                {card.detail && <small>{card.detail}</small>}
              </article>
            ))}
          </div>
        </div>
      )}

      {/* ⚙️ Infrastructure & Network Metrics */}
      {infraCards.length > 0 && (
        <div className="card">
          <h3 className="metrics-section-title">⚙️ Infrastructure & Network Metrics</h3>
          <div className="metrics-card-grid">
            {infraCards.map(card => (
              <article key={card.label} className={`metrics-card ${card.status ?? 'ok'}`}>
                <span className="metrics-card-label">{card.label}</span>
                <strong>{card.value}</strong>
                {card.detail && <small>{card.detail}</small>}
              </article>
            ))}
          </div>
        </div>
      )}
    </main>
  );
};

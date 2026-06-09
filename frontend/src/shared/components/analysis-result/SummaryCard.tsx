import type { ReactNode } from 'react';
import type { AgentScoreBreakdown, DetailedSummary } from '../../types/analysis';

interface SummaryCardProps {
  items: string[];
  detailedSummary?: DetailedSummary | null;
  scoreBreakdown?: AgentScoreBreakdown | null;
  qualityNotes?: string[] | null;
}

function normalizeList(items?: string[] | null): string[] {
  return Array.isArray(items) ? items.filter(Boolean) : [];
}

function TextList({ items }: { items?: string[] | null }) {
  if (!items || items.length === 0) return <p>Chưa có dữ liệu.</p>;
  return (
    <ul>
      {items.map((item, index) => (
        <li key={`${item}-${index}`}>{item}</li>
      ))}
    </ul>
  );
}

function SummaryBlock({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="summary-block">
      <h3>{title}</h3>
      {children}
    </div>
  );
}

function PriorityBadge({ value }: { value: string }) {
  const normalized = value?.toLowerCase();
  const label = normalized === 'high' ? 'Cao' : normalized === 'low' ? 'Thấp' : 'Trung bình';
  return <span className={`summary-priority ${normalized || 'medium'}`}>{label}</span>;
}

export function SummaryCard({ items, detailedSummary, scoreBreakdown, qualityNotes }: SummaryCardProps) {
  const safeItems = normalizeList(items);
  const normalizedSummary: DetailedSummary = {
    overview: detailedSummary?.overview || (safeItems.length > 0 ? safeItems.join(' ') : 'Chưa có tóm tắt.'),
    key_takeaways: normalizeList(detailedSummary?.key_takeaways),
    topics: Array.isArray(detailedSummary?.topics) ? detailedSummary!.topics : [],
    customer_needs: normalizeList(detailedSummary?.customer_needs),
    customer_pain_points: normalizeList(detailedSummary?.customer_pain_points),
    agent_actions: normalizeList(detailedSummary?.agent_actions),
    outcome: detailedSummary?.outcome || 'Chưa xác định do thiếu dữ liệu.',
    next_steps: normalizeList(detailedSummary?.next_steps),
    action_items: Array.isArray(detailedSummary?.action_items) ? detailedSummary!.action_items : [],
    risks_or_escalations: normalizeList(detailedSummary?.risks_or_escalations),
  };
  const criteria = scoreBreakdown ? Object.entries(scoreBreakdown) : [];

  return (
    <section className="card detailed-summary-card">
      <h2>Call Notes</h2>

      <div className="summary-overview">
        <p>{normalizedSummary.overview}</p>
      </div>

      <div className="summary-grid two">
        <SummaryBlock title="Ý chính">
          <TextList items={normalizedSummary.key_takeaways.length > 0 ? normalizedSummary.key_takeaways : safeItems} />
        </SummaryBlock>

        <SummaryBlock title="Kết quả & bước tiếp theo">
          <p>{normalizedSummary.outcome}</p>
          <TextList items={normalizedSummary.next_steps} />
        </SummaryBlock>
      </div>

      <div className="summary-grid three">
        <SummaryBlock title="Nhu cầu khách hàng">
          <TextList items={normalizedSummary.customer_needs} />
        </SummaryBlock>

        <SummaryBlock title="Vấn đề nổi bật">
          <TextList items={normalizedSummary.customer_pain_points} />
        </SummaryBlock>

        <SummaryBlock title="Nhân viên đã xử lý">
          <TextList items={normalizedSummary.agent_actions} />
        </SummaryBlock>
      </div>

      <SummaryBlock title="Chủ đề chính">
        {normalizedSummary.topics.length === 0 ? (
          <p>Chưa có dữ liệu.</p>
        ) : (
          <div className="summary-topic-list">
            {normalizedSummary.topics.map((topic, index) => (
              <div className="summary-topic" key={`${topic.title}-${index}`}>
                <div className="summary-topic-header">
                  <strong>{topic.title}</strong>
                  {topic.time_range && <span>{topic.time_range}</span>}
                </div>
                <TextList items={topic.details} />
              </div>
            ))}
          </div>
        )}
      </SummaryBlock>

      <SummaryBlock title="Việc cần làm">
        {normalizedSummary.action_items.length === 0 ? (
          <p>Chưa có dữ liệu.</p>
        ) : (
          <div className="summary-action-table">
            {normalizedSummary.action_items.map((item, index) => (
              <div className="summary-action-row" key={`${item.task}-${index}`}>
                <span>{item.owner}</span>
                <strong>{item.task}</strong>
                <span>{item.deadline || 'Chưa có hạn'}</span>
                <PriorityBadge value={item.priority} />
              </div>
            ))}
          </div>
        )}
      </SummaryBlock>

      <SummaryBlock title="Rủi ro cần theo dõi">
        <TextList items={normalizedSummary.risks_or_escalations} />
      </SummaryBlock>

      <div className="summary-grid two">
        <SummaryBlock title="Nhận xét chất lượng">
          <TextList items={qualityNotes} />
        </SummaryBlock>

        <SummaryBlock title="Rubric điểm">
          {criteria.length === 0 ? (
            <p>Chưa có dữ liệu.</p>
          ) : (
            <div className="score-breakdown-list">
              {criteria.map(([key, item]) => (
                <div className="score-breakdown-row" key={key}>
                  <span>{item.label}</span>
                  <strong>{item.score}/{item.max}</strong>
                </div>
              ))}
            </div>
          )}
        </SummaryBlock>
      </div>
    </section>
  );
}

export type AnalysisStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface TranscriptTurn {
  index?: number;
  speaker: string;
  text: string;
  start_seconds?: number | null;
  end_seconds?: number | null;
}

export interface SummaryTopic {
  title: string;
  time_range?: string | null;
  details: string[];
  evidence_turns?: number[];
}

export interface SummaryActionItem {
  owner: string;
  task: string;
  deadline?: string | null;
  priority: 'low' | 'medium' | 'high' | string;
  evidence_turns?: number[];
}

export interface DetailedSummary {
  overview: string;
  key_takeaways: string[];
  topics: SummaryTopic[];
  customer_needs: string[];
  customer_pain_points: string[];
  agent_actions: string[];
  outcome: string;
  next_steps: string[];
  action_items: SummaryActionItem[];
  risks_or_escalations: string[];
}

export interface AgentScoreCriterion {
  label: string;
  score: number;
  max: number;
  reason: string;
}

export type AgentScoreBreakdown = Record<string, AgentScoreCriterion>;

export interface AnalysisMetadata {
  summary_version?: string;
  model_name?: string;
  generated_at?: string;
  pipeline_mode?: string;
  [key: string]: unknown;
}

export interface AnalysisResult {
  transcript: TranscriptTurn[];
  summary: string[];
  detailed_summary?: DetailedSummary | null;
  sentiment: 'positive' | 'neutral' | 'negative' | string;
  sentiment_reason: string;
  confidence: number;
  agent_score?: number | null;
  agent_score_breakdown?: AgentScoreBreakdown | null;
  quality_notes?: string[] | null;
  agent_advice?: string[] | null;
  analysis_metadata?: AnalysisMetadata | null;
}

export interface JobStatus {
  job_id: string;
  name?: string | null;
  status: AnalysisStatus;
  input_type?: string | null;
  audio_object_key?: string | null;
  result?: AnalysisResult | null;
  error_message?: string | null;
}

export interface SessionListItem {
  job_id: string;
  name: string | null;
  status: AnalysisStatus;
  input_type: string | null;
  created_at: string;
  sentiment: string | null;
  confidence: number | null;
}

export interface SessionListResponse {
  sessions: SessionListItem[];
  total: number;
  offset: number;
  limit: number;
}

export interface MinioFile {
  object_key: string;
  name: string;
  size: number | null;
  last_modified: string | null;
  etag: string | null;
}

export interface UploadOnlyResult {
  object_key: string;
  name: string;
  original_name: string | null;
  size: number;
}

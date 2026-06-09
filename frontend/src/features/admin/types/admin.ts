import type { AgentScoreBreakdown, AnalysisMetadata, DetailedSummary } from '../../../shared/types/analysis';

export interface Employee {
  id: string;
  username: string;
  email: string;
  total_jobs: number;
  average_score: number | null;
  sentiment_distribution: { positive: number; neutral: number; negative: number };
  created_at: string;
}

export interface EmployeeStats {
  total_jobs: number;
  sentiment_distribution: { positive: number; neutral: number; negative: number };
  average_confidence: number;
  average_agent_score: number;
  weekly_trends: { date: string; count: number }[];
}

export interface EmployeeSession {
  job_id: string;
  name: string;
  status: string;
  input_type: string;
  audio_object_key?: string | null;
  created_at: string;
  sentiment: string | null;
  confidence: number | null;
  agent_score: number | null;
  agent_advice: string[] | null;
  summary: string[] | null;
  detailed_summary: DetailedSummary | null;
  agent_score_breakdown: AgentScoreBreakdown | null;
  quality_notes: string[] | null;
  analysis_metadata: AnalysisMetadata | null;
  sentiment_reason: string | null;
  transcript: any | null;
}

export interface AccountUser {
  id: string;
  username: string;
  email: string;
  role_id: string;
  is_active: boolean;
  created_at: string;
}

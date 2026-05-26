export type AnalysisStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface TranscriptTurn {
  speaker: string;
  text: string;
  start_seconds?: number | null;
  end_seconds?: number | null;
}

export interface AnalysisResult {
  transcript: TranscriptTurn[];
  summary: string[];
  sentiment: 'positive' | 'neutral' | 'negative' | string;
  sentiment_reason: string;
  confidence: number;
  agent_score?: number | null;
  agent_advice?: string[] | null;
}

export interface JobStatus {
  job_id: string;
  name?: string | null;
  status: AnalysisStatus;
  input_type?: string | null;
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


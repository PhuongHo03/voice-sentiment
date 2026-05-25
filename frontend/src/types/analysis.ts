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
}

export interface JobStatus {
  job_id: string;
  status: AnalysisStatus;
  input_type?: string | null;
  result?: AnalysisResult | null;
  error_message?: string | null;
}

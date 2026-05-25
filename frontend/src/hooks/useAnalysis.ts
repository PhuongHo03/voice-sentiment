import { useEffect, useState } from 'react';
import { getAnalysis, submitAudio, submitText } from '../services/analysisApi';
import type { JobStatus } from '../types/analysis';

export function useAnalysis() {
  const [job, setJob] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function analyzeAudio(file: File) {
    setLoading(true);
    setError(null);
    try { setJob(await submitAudio(file)); } catch (err) { setError(err instanceof Error ? err.message : 'Upload failed'); } finally { setLoading(false); }
  }

  async function analyzeText(text: string) {
    setLoading(true);
    setError(null);
    try { setJob(await submitText(text)); } catch (err) { setError(err instanceof Error ? err.message : 'Submit failed'); } finally { setLoading(false); }
  }

  useEffect(() => {
    if (!job || job.status === 'completed' || job.status === 'failed') return;
    const timer = window.setInterval(async () => {
      try { setJob(await getAnalysis(job.job_id)); } catch (err) { setError(err instanceof Error ? err.message : 'Polling failed'); }
    }, 2000);
    return () => window.clearInterval(timer);
  }, [job]);

  return { job, error, loading, analyzeAudio, analyzeText };
}

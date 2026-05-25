import type { JobStatus } from '../types/analysis';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export async function submitAudio(file: File): Promise<JobStatus> {
  const data = new FormData();
  data.append('file', file);
  const response = await fetch(`${apiBaseUrl}/api/analysis/audio`, { method: 'POST', body: data });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function submitText(text: string): Promise<JobStatus> {
  const response = await fetch(`${apiBaseUrl}/api/analysis/text`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function getAnalysis(jobId: string): Promise<JobStatus> {
  const response = await fetch(`${apiBaseUrl}/api/analysis/${jobId}`);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

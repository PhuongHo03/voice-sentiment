import type { JobStatus } from '../types/analysis';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? '';

function getHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const token = localStorage.getItem('voice_sentiment_token');
  const headers: Record<string, string> = { ...extra };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function submitAudio(file: File): Promise<JobStatus> {
  const data = new FormData();
  data.append('file', file);
  
  const headers = getHeaders();
  
  const response = await fetch(`${apiBaseUrl}/api/analysis/audio`, { 
    method: 'POST', 
    headers: headers,
    body: data 
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function submitText(text: string): Promise<JobStatus> {
  const response = await fetch(`${apiBaseUrl}/api/analysis/text`, { 
    method: 'POST', 
    headers: getHeaders({ 'Content-Type': 'application/json' }), 
    body: JSON.stringify({ text }) 
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function getAnalysis(jobId: string): Promise<JobStatus> {
  const response = await fetch(`${apiBaseUrl}/api/analysis/${jobId}`, {
    headers: getHeaders()
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function fetchSessions(limit = 20, offset = 0): Promise<any> {
  const response = await fetch(`${apiBaseUrl}/api/analysis?limit=${limit}&offset=${offset}`, {
    headers: getHeaders()
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function renameSession(jobId: string, name: string): Promise<JobStatus> {
  const response = await fetch(`${apiBaseUrl}/api/analysis/${jobId}`, {
    method: 'PATCH',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ name })
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function deleteSession(jobId: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/api/analysis/${jobId}`, {
    method: 'DELETE',
    headers: getHeaders()
  });
  if (!response.ok) throw new Error(await response.text());
}

export async function fetchStats(): Promise<any> {
  const response = await fetch(`${apiBaseUrl}/api/analysis/stats`, {
    headers: getHeaders()
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}


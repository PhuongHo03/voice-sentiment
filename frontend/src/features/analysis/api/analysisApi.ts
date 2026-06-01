import {
  buildAudioFormData,
  buildAudioFromKeyPayload,
  buildRenameSessionPayload,
  buildTextPayload,
  parseFilesResponse,
  parseJobStatusResponse,
  parseSessionsResponse,
  parseUploadOnlyResponse,
} from '../dtos/analysisDto';
import type { JobStatus, MinioFile, SessionListResponse, UploadOnlyResult } from '../types/analysis';

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
  const data = buildAudioFormData(file);
  
  const headers = getHeaders();
  
  const response = await fetch(`${apiBaseUrl}/api/analysis/audio`, { 
    method: 'POST', 
    headers: headers,
    body: data 
  });
  if (!response.ok) throw new Error(await response.text());
  return parseJobStatusResponse(await response.json());
}

export async function submitText(text: string): Promise<JobStatus> {
  const response = await fetch(`${apiBaseUrl}/api/analysis/text`, { 
    method: 'POST', 
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(buildTextPayload(text))
  });
  if (!response.ok) throw new Error(await response.text());
  return parseJobStatusResponse(await response.json());
}

export async function getAnalysis(jobId: string): Promise<JobStatus> {
  const response = await fetch(`${apiBaseUrl}/api/analysis/${jobId}`, {
    headers: getHeaders()
  });
  if (!response.ok) throw new Error(await response.text());
  return parseJobStatusResponse(await response.json());
}

export async function fetchSessions(limit = 20, offset = 0): Promise<SessionListResponse> {
  const response = await fetch(`${apiBaseUrl}/api/analysis?limit=${limit}&offset=${offset}`, {
    headers: getHeaders()
  });
  if (!response.ok) throw new Error(await response.text());
  return parseSessionsResponse(await response.json());
}

export async function renameSession(jobId: string, name: string): Promise<JobStatus> {
  const response = await fetch(`${apiBaseUrl}/api/analysis/${jobId}`, {
    method: 'PATCH',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(buildRenameSessionPayload(name))
  });
  if (!response.ok) throw new Error(await response.text());
  return parseJobStatusResponse(await response.json());
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

export async function listUserFiles(): Promise<{ files: MinioFile[]; total: number }> {
  const response = await fetch(`${apiBaseUrl}/api/files`, {
    headers: getHeaders()
  });
  if (!response.ok) throw new Error(await response.text());
  return parseFilesResponse(await response.json());
}

export async function getFilePresignedUrl(objectKey: string): Promise<string> {
  const token = localStorage.getItem('voice_sentiment_token') ?? '';
  return `${apiBaseUrl}/api/files/stream?object_key=${encodeURIComponent(objectKey)}&token=${encodeURIComponent(token)}`;
}

export async function deleteUserFile(objectKey: string): Promise<void> {
  const response = await fetch(
    `${apiBaseUrl}/api/files?object_key=${encodeURIComponent(objectKey)}`,
    { method: 'DELETE', headers: getHeaders() }
  );
  if (!response.ok) {
    // Try to extract a human-readable detail from the JSON error body
    try {
      const body = await response.json();
      throw new Error(body.detail ?? JSON.stringify(body));
    } catch (parseErr) {
      if (parseErr instanceof Error && parseErr.message !== 'Unexpected end of JSON input') {
        throw parseErr;
      }
      throw new Error(await response.text());
    }
  }
}


/** Upload a file to MinIO only (no analysis job created). */
export async function uploadFileOnly(file: File): Promise<UploadOnlyResult> {
  const data = buildAudioFormData(file);
  const response = await fetch(`${apiBaseUrl}/api/files/upload`, {
    method: 'POST',
    headers: getHeaders(),
    body: data,
  });
  if (!response.ok) throw new Error(await response.text());
  return parseUploadOnlyResponse(await response.json());
}

/** Start analysis from an already-uploaded MinIO object key (no re-upload). */
export async function submitAudioFromKey(objectKey: string, name?: string): Promise<JobStatus> {
  const response = await fetch(`${apiBaseUrl}/api/analysis/audio-from-key`, {
    method: 'POST',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(buildAudioFromKeyPayload(objectKey, name)),
  });
  if (!response.ok) throw new Error(await response.text());
  return parseJobStatusResponse(await response.json());
}

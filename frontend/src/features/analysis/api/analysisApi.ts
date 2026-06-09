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
import type { JobStatus, MinioFile, SessionListResponse, UploadOnlyResult } from '../../../shared/types/analysis';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? '';

function getAuthToken(token?: string | null): string | null {
  return token ?? localStorage.getItem('voice_sentiment_token');
}

function getHeaders(token?: string | null, extra: Record<string, string> = {}): Record<string, string> {
  const resolvedToken = getAuthToken(token);
  const headers: Record<string, string> = { ...extra };
  if (resolvedToken) {
    headers['Authorization'] = `Bearer ${resolvedToken}`;
  }
  return headers;
}

export async function submitAudio(file: File, token?: string | null): Promise<JobStatus> {
  const data = buildAudioFormData(file);
  
  const headers = getHeaders(token);
  
  const response = await fetch(`${apiBaseUrl}/api/analysis/audio`, { 
    method: 'POST', 
    headers: headers,
    body: data 
  });
  if (!response.ok) throw new Error(await response.text());
  return parseJobStatusResponse(await response.json());
}

export async function submitText(text: string, token?: string | null): Promise<JobStatus> {
  const response = await fetch(`${apiBaseUrl}/api/analysis/text`, { 
    method: 'POST', 
    headers: getHeaders(token, { 'Content-Type': 'application/json' }),
    body: JSON.stringify(buildTextPayload(text))
  });
  if (!response.ok) throw new Error(await response.text());
  return parseJobStatusResponse(await response.json());
}

export async function getAnalysis(jobId: string, token?: string | null): Promise<JobStatus> {
  const response = await fetch(`${apiBaseUrl}/api/analysis/${jobId}`, {
    headers: getHeaders(token)
  });
  if (!response.ok) throw new Error(await response.text());
  return parseJobStatusResponse(await response.json());
}

export async function fetchSessions(limit = 20, offset = 0, token?: string | null): Promise<SessionListResponse> {
  const response = await fetch(`${apiBaseUrl}/api/analysis?limit=${limit}&offset=${offset}`, {
    headers: getHeaders(token)
  });
  if (!response.ok) throw new Error(await response.text());
  return parseSessionsResponse(await response.json());
}

export async function renameSession(jobId: string, name: string, token?: string | null): Promise<JobStatus> {
  const response = await fetch(`${apiBaseUrl}/api/analysis/${jobId}`, {
    method: 'PATCH',
    headers: getHeaders(token, { 'Content-Type': 'application/json' }),
    body: JSON.stringify(buildRenameSessionPayload(name))
  });
  if (!response.ok) throw new Error(await response.text());
  return parseJobStatusResponse(await response.json());
}

export async function deleteSession(jobId: string, token?: string | null): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/api/analysis/${jobId}`, {
    method: 'DELETE',
    headers: getHeaders(token)
  });
  if (!response.ok) throw new Error(await response.text());
}

export async function fetchStats(token?: string | null): Promise<any> {
  const response = await fetch(`${apiBaseUrl}/api/analysis/stats`, {
    headers: getHeaders(token)
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function listUserFiles(token?: string | null): Promise<{ files: MinioFile[]; total: number }> {
  const response = await fetch(`${apiBaseUrl}/api/files`, {
    headers: getHeaders(token)
  });
  if (!response.ok) throw new Error(await response.text());
  return parseFilesResponse(await response.json());
}

export function getFilePresignedUrl(objectKey: string, token?: string | null): string {
  const resolvedToken = getAuthToken(token) ?? '';
  return `${apiBaseUrl}/api/files/stream?object_key=${encodeURIComponent(objectKey)}&token=${encodeURIComponent(resolvedToken)}`;
}

export async function deleteUserFile(objectKey: string, token?: string | null): Promise<void> {
  const response = await fetch(
    `${apiBaseUrl}/api/files?object_key=${encodeURIComponent(objectKey)}`,
    { method: 'DELETE', headers: getHeaders(token) }
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
export async function uploadFileOnly(file: File, token?: string | null): Promise<UploadOnlyResult> {
  const data = buildAudioFormData(file);
  const response = await fetch(`${apiBaseUrl}/api/files/upload`, {
    method: 'POST',
    headers: getHeaders(token),
    body: data,
  });
  if (!response.ok) throw new Error(await response.text());
  return parseUploadOnlyResponse(await response.json());
}

/** Start analysis from an already-uploaded MinIO object key (no re-upload). */
export async function submitAudioFromKey(objectKey: string, name?: string, token?: string | null): Promise<JobStatus> {
  const response = await fetch(`${apiBaseUrl}/api/analysis/audio-from-key`, {
    method: 'POST',
    headers: getHeaders(token, { 'Content-Type': 'application/json' }),
    body: JSON.stringify(buildAudioFromKeyPayload(objectKey, name)),
  });
  if (!response.ok) throw new Error(await response.text());
  return parseJobStatusResponse(await response.json());
}

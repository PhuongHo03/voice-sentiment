import type { JobStatus, MinioFile, SessionListResponse, UploadOnlyResult } from '../types/analysis';

export function buildAudioFormData(file: File): FormData {
  const data = new FormData();
  data.append('file', file);
  return data;
}

export function buildTextPayload(text: string): { text: string } {
  return { text };
}

export function buildRenameSessionPayload(name: string): { name: string } {
  return { name };
}

export function buildAudioFromKeyPayload(objectKey: string, name?: string): { object_key: string; name?: string } {
  return { object_key: objectKey, name };
}

export function parseJobStatusResponse(data: any): JobStatus {
  return data;
}

export function parseSessionsResponse(data: any): SessionListResponse {
  return {
    sessions: Array.isArray(data?.sessions) ? data.sessions : [],
    total: data?.total ?? 0,
    offset: data?.offset ?? 0,
    limit: data?.limit ?? 20,
  };
}

export function parseFilesResponse(data: any): { files: MinioFile[]; total: number } {
  return {
    files: Array.isArray(data?.files) ? data.files : [],
    total: data?.total ?? 0,
  };
}

export function parseUploadOnlyResponse(data: any): UploadOnlyResult {
  return data;
}

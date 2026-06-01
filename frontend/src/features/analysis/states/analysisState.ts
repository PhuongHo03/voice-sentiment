import type { MinioFile, SessionListItem, UploadOnlyResult } from '../types/analysis';

export type AnalysisView = 'session' | 'dashboard' | 'files';

export const ACTIVE_VIEW_STORAGE_KEY = 'activeView';
export const ACTIVE_SESSION_ID_STORAGE_KEY = 'activeSessionId';

export function getInitialAnalysisView(savedView: string | null): AnalysisView {
  return savedView === 'dashboard' || savedView === 'files' ? savedView : 'session';
}

export function persistActiveSessionId(id: string | null): void {
  if (id) {
    localStorage.setItem(ACTIVE_SESSION_ID_STORAGE_KEY, id);
  } else {
    localStorage.removeItem(ACTIVE_SESSION_ID_STORAGE_KEY);
  }
}

export function persistActiveView(view: AnalysisView): void {
  localStorage.setItem(ACTIVE_VIEW_STORAGE_KEY, view);
}

export function getStoredActiveSessionId(): string | null {
  return localStorage.getItem(ACTIVE_SESSION_ID_STORAGE_KEY);
}

export function getStoredActiveView(): string | null {
  return localStorage.getItem(ACTIVE_VIEW_STORAGE_KEY);
}

export function resolveInitialActiveSessionId(sessions: SessionListItem[], storedId: string | null, storedView: string | null): string | null {
  const validStored = storedId && sessions.some((s: SessionListItem) => s.job_id === storedId);
  if (validStored) return storedId;
  if (storedId === null && storedView === 'session') return null;
  if (sessions.length > 0) return sessions[0].job_id;
  return null;
}

export function createUploadedFileItem(result: UploadOnlyResult): MinioFile {
  return {
    object_key: result.object_key,
    name: result.original_name || result.name,
    size: result.size,
    last_modified: new Date().toISOString(),
    etag: null,
  };
}

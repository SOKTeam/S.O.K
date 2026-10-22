// The renames: POST /api/renames, and the last one (GET /api/renames/current),
// kept live by the events of the server.

import { api } from "./api";

export interface RenameResult {
  renamed: number;
  subtitles: number;
  skipped: { file: string; reason: string }[];
  errors: { file: string; error: string }[];
  /** The operation of the history. */
  operation: string | null;
}

export interface Rename {
  id: number;
  media_type: string;
  status: "running" | "done" | "failed" | "interrupted";
  started: string;
  finished: string | null;
  error: { code: string; message?: string } | null;
  result: RenameResult | null;
  progress: { done: number; total: number } | null;
}

const state = $state<{ current: Rename | null }>({ current: null });

export const renames = {
  get current() {
    return state.current;
  },
  get running() {
    return state.current?.status === "running";
  },
};

export function setRename(rename: Rename | null): void {
  state.current = rename;
}

export function setRenameProgress(progress: { done: number; total: number }): void {
  if (state.current?.status === "running") {
    state.current.progress = progress;
  }
}

export async function refreshRename(): Promise<void> {
  state.current = (await api<{ rename: Rename | null }>("/api/renames/current")).rename;
}

/**
 * Rename the Ready rows of a tab, or some of them. Throws ApiError with a
 * code, or {"code", "source", "destination"} when a hard link cannot be made.
 */
export async function startRename(mediaType: string, rows?: number[]): Promise<void> {
  await api("/api/renames", { method: "POST", body: { type: mediaType, rows } });
  await refreshRename();
}

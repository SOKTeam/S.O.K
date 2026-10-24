// The history of the renames, its undo, and the files already processed.

import { api } from "./api";

export interface HistoryFile {
  index: number;
  source: string;
  target: string;
  mode: "move" | "link" | "copy";
  undone: boolean;
  /** The new path of the video a subtitle goes with. */
  follows: string | null;
}

export interface Operation {
  id: string;
  date: string;
  kind: string;
  media_type: string;
  undone: boolean;
  partly_undone: boolean;
  /** Made by the automatic sorting. */
  auto: boolean;
  files: HistoryFile[];
}

export interface UndoReport {
  restored: string[];
  skipped: { source: string; target: string; reason: "missing" | "occupied" | "failed" }[];
  operation: Operation;
}

export interface ProcessedFile {
  path: string;
  target: string;
  size: number;
  date: string;
  operation: string;
}

export async function loadHistory(): Promise<Operation[]> {
  return (await api<{ operations: Operation[] }>("/api/history")).operations;
}

/** Undo an operation, or one of its files (with its subtitles). */
export function undo(id: string, index?: number): Promise<UndoReport> {
  return api<UndoReport>(`/api/history/${id}/undo`, { method: "POST", body: { index } });
}

export async function loadProcessed(): Promise<ProcessedFile[]> {
  return (await api<{ files: ProcessedFile[] }>("/api/processed")).files;
}

/** The next analysis takes these files again. */
export function forgetProcessed(paths: string[]): Promise<{ forgotten: number }> {
  return api("/api/processed/forget", { method: "POST", body: { paths } });
}

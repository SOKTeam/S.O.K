// The analysis: its summary (GET /api/scans/current), kept up to date by the
// events of the server (GET /api/events).

import { api } from "./api";

export type RowStatus = "pending" | "ok" | "ambiguous" | "missing";

export type Counts = Record<RowStatus | "total", number>;

export interface ScanError {
  /** missing_key, key_refused, rate_limited, or failed with a message. */
  code: string;
  service?: string;
  message?: string;
  others?: { code: string; service: string }[];
}

export interface Progress {
  phase: "detect" | "search";
  done: number;
  total: number;
}

export interface Scan {
  id: number;
  status: "running" | "done" | "failed" | "interrupted";
  started: string;
  finished: string | null;
  error: ScanError | null;
  missing_sources: string[];
  /** Files left out: renamed before, unchanged since. */
  processed: number;
  progress: Progress | null;
}

export interface ToCheck {
  path: string;
  kind: string;
  media_type: string;
  title: string | null;
  reason: string;
}

export interface Summary {
  scan: Scan | null;
  counts: Record<string, Counts>;
  to_check: ToCheck[];
}

const state = $state<{ summary: Summary | null; changes: number }>({
  summary: null,
  changes: 0,
});

export const analysis = {
  get summary() {
    return state.summary;
  },
  get running() {
    return state.summary?.scan?.status === "running";
  },
  /** Grows at each change of the rows by an analysis: the tabs read them again. */
  get changes() {
    return state.changes;
  },
};

function setSummary(summary: Summary): void {
  state.summary = summary;
  state.changes += 1;
}

export async function refreshSummary(): Promise<void> {
  state.summary = await api<Summary>("/api/scans/current");
}

/** Listen to the events of the server; returns how to stop. The browser
 * reconnects by itself after a cut, and the first event is the summary. */
export function listen(): () => void {
  const source = new EventSource("/api/events");
  source.addEventListener("scan", (event) => {
    const { type: _type, ...summary } = JSON.parse((event as MessageEvent).data);
    setSummary(summary as Summary);
  });
  source.addEventListener("progress", (event) => {
    const { type: _type, ...progress } = JSON.parse((event as MessageEvent).data);
    const scan = state.summary?.scan;
    if (scan && progress.phase !== "rename") {
      const sorted = scan.progress?.phase !== "search" && progress.phase === "search";
      scan.progress = progress as Progress;
      if (sorted) {
        // The files are sorted: the counts of the rows are known.
        refreshSummary()
          .then(() => (state.changes += 1))
          .catch(() => {});
      }
    }
  });
  return () => source.close();
}

/** Start an analysis; throws ApiError already_running, rename_running or no_sources. */
export async function startScan(): Promise<void> {
  await api("/api/scans", { method: "POST" });
}

/** Give a file to check its type; it joins the rows of that type. */
export async function confirmType(path: string, kind: string): Promise<void> {
  setSummary(await api<Summary>("/api/to-check", { method: "POST", body: { path, kind } }));
}

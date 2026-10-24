// The automatic sorting (GET /api/watch), kept up to date by the "watch"
// events of the server.

import { api } from "./api";

/** Why a part of an automatic sorting did not happen: the stop of its
 * analysis (missing_key…), or the refused rename of a tab (no_destination,
 * a hard link problem…). */
export interface WatchProblem {
  code: string;
  media_type?: string;
  service?: string;
  message?: string;
  source?: string;
  destination?: string;
}

export interface WatchRun {
  date: string;
  /** The id of its analysis; null when it could not start. */
  scan: number | null;
  /** The files renamed. */
  renamed: number;
  errors: WatchProblem[];
}

export interface WatchStatus {
  enabled: boolean;
  minutes: number;
  /** The last look at the folders, since the start of the server. */
  last_check: string | null;
  last_run: WatchRun | null;
}

const state = $state<{ status: WatchStatus | null }>({ status: null });

export const watch = {
  get status() {
    return state.status;
  },
};

export function setWatch(status: WatchStatus): void {
  state.status = status;
}

export async function loadWatch(): Promise<void> {
  setWatch(await api<WatchStatus>("/api/watch"));
}

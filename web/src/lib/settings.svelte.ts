// The settings of the server: GET and PATCH /api/settings.

import { api } from "./api";

export type FileMode = "move" | "link" | "copy";

export interface KeyField {
  key: string;
  set: boolean;
  /** An environment variable gives it, and wins: it cannot be changed. */
  locked: boolean;
}

export interface ServiceKeys {
  service: string;
  name: string;
  media_type: string;
  url: string | null;
  keys: KeyField[];
}

export interface LinkCheck {
  source: string;
  destination: string;
  ok: boolean;
  problem: "different_drives" | "no_hard_links" | "missing_folder" | null;
  /** False when the source holds no file: only the drives were compared. */
  tested: boolean;
}

export interface SettingsData {
  settings: Record<string, string | boolean>;
  languages: string[];
  services: Record<string, { id: string; name: string }[]>;
  keys: ServiceKeys[];
  folders: Record<string, string[]>;
  link_checks: LinkCheck[];
}

export interface SettingsChange {
  settings?: Record<string, string | boolean>;
  keys?: Record<string, string>;
  folders?: Record<string, string[]>;
}

const state = $state<{ data: SettingsData | null }>({ data: null });

export const settings = {
  get data() {
    return state.data;
  },
};

export async function loadSettings(): Promise<void> {
  state.data = await api<SettingsData>("/api/settings");
}

/** Save a change: all of it or nothing; the answer is the new settings.
 * Throws the ApiError of a refused change ({"code", "item"}). */
export async function saveSettings(change: SettingsChange): Promise<void> {
  state.data = await api<SettingsData>("/api/settings", { method: "PATCH", body: change });
}

export interface KeyTest {
  service: string;
  status:
    | "ok"
    | "wrong_key"
    | "missing_key"
    | "rate_limited"
    | "service_error"
    | "unreachable"
    | "unsupported";
}

/** Test the saved key of a service. */
export function testKey(service: string): Promise<KeyTest> {
  return api<KeyTest>("/api/settings/test-key", { method: "POST", body: { service } });
}

// The account and the session: what the interface shows first.

import { api } from "./api";

export interface Session {
  /** "login", or "none" when SOK_AUTH=none turns the login off. */
  auth: "login" | "none";
  account: boolean;
  logged_in: boolean;
  username: string | null;
  language: string;
}

const state = $state<{ current: Session | null }>({ current: null });

export const session = {
  /** The session, null until the first answer. */
  get current() {
    return state.current;
  },
};

export async function refreshSession(): Promise<Session> {
  state.current = await api<Session>("/api/session");
  return state.current;
}

export async function logOut(): Promise<void> {
  await api("/api/logout", { method: "POST" });
  await refreshSession();
}

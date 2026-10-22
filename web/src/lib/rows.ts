// The rows of a tab: GET /api/rows, PATCH /api/rows/{id}, POST …/search.

import { api } from "./api";
import type { RowStatus } from "./scan.svelte";

export interface Candidate {
  id: string | number | null;
  title: string | null;
  original_title: string | null;
  /** The artist of an album or a track, the authors of a book. */
  by: string | null;
  year: number | null;
  /** A path of TMDB (/abc.jpg) or a full address. */
  poster: string | null;
  overview: string;
}

export interface RowFile {
  path: string;
  name: string;
  /** The path under the destination, or null before a match. */
  new_name: string | null;
  /** Why the last rename left the file. */
  error: { code: string; message: string } | null;
}

export interface Row {
  id: number;
  media_type: string;
  /** movie, episode, album, track, book or game. */
  kind: string;
  /** Of a series or an album. */
  title: string | null;
  query: string | null;
  year: number | null;
  status: RowStatus;
  selected: number | null;
  destination: number;
  candidates: Candidate[];
  files: RowFile[];
  episodes_found: number | null;
}

export async function loadRows(mediaType: string): Promise<Row[]> {
  return (await api<{ rows: Row[] }>(`/api/rows?type=${mediaType}`)).rows;
}

export function changeRow(
  id: number,
  change: { selected?: number; destination?: number },
): Promise<Row> {
  return api<Row>(`/api/rows/${id}`, { method: "PATCH", body: change });
}

/** Search a row again with the text typed; throws ApiError with
 * {"code", "service"} when a key stops the search. */
export function searchRow(id: number, query: string): Promise<Row> {
  return api<Row>(`/api/rows/${id}/search`, { method: "POST", body: { query } });
}

/** The address of a poster: TMDB gives a path, the other services an address. */
export function posterUrl(poster: string | null): string | null {
  if (!poster) {
    return null;
  }
  return poster.startsWith("/") ? `https://image.tmdb.org/t/p/w154${poster}` : poster;
}

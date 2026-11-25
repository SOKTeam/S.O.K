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
  /** The size of its files in bytes, and the quality read from the first
   * file name ("2160p · x265"); absent in the recorded demo. */
  size?: number;
  quality?: string | null;
}

/** The result picked for a row, or null. */
export function matchOf(row: Row): Candidate | null {
  return row.selected === null ? null : (row.candidates[row.selected] ?? null);
}

/** The title shown for a row: its match, else what was read from the file. */
export function titleOf(row: Row): string {
  return matchOf(row)?.title ?? row.title ?? row.query ?? row.files[0]?.name ?? "";
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

/** A larger poster, for the scene. */
export function bigPosterUrl(poster: string | null): string | null {
  if (!poster) return null;
  return poster.startsWith("/") ? `https://image.tmdb.org/t/p/w500${poster}` : poster;
}

/** "S01E04" of an episode file, read from its new name, else its name. */
export function episodeCode(file: RowFile): string | null {
  for (const text of [file.new_name, file.name]) {
    const name = text?.split("/").pop() ?? "";
    const se = name.match(/S(\d{1,2})E(\d{1,3})/i);
    if (se) return `S${se[1].padStart(2, "0")}E${se[2].padStart(2, "0")}`;
    const x = name.match(/\b(\d{1,2})x(\d{2,3})\b/);
    if (x) return `S${x[1].padStart(2, "0")}E${x[2].padStart(2, "0")}`;
  }
  return null;
}

/** The title of an episode in its new name ("Pilot"), or null. */
export function episodeTitle(file: RowFile): string | null {
  const name =
    file.new_name
      ?.split("/")
      .pop()
      ?.replace(/\.[^.]+$/, "") ?? "";
  const found = name.match(/S\d+E\d+\s+(.+)$/i);
  return found ? found[1] : null;
}

/** The seasons of the episodes of a row, in order. */
export function seasonsOf(row: Row): number[] {
  const seasons = row.files
    .map((file) => episodeCode(file))
    .filter((code): code is string => code !== null)
    .map((code) => Number(code.slice(1, 3)));
  return [...new Set(seasons)].sort((a, b) => a - b);
}

/** The number and title of a track, read from its new name ("01 - One
 * More Time"), else its name. */
export function trackOf(file: RowFile): { number: string | null; title: string } {
  const name = (file.new_name ?? file.name)
    .split("/")
    .pop()!
    .replace(/\.[^.]+$/, "");
  const found = name.match(/^(\d{1,3})\s*[-.]\s*(.+)$/);
  return found
    ? { number: found[1].padStart(2, "0"), title: found[2] }
    : { number: null, title: name };
}

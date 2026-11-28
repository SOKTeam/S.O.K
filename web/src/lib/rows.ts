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
  /** Of a book, when its service gives them. */
  publisher?: string | null;
  isbn?: string | null;
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
  /** The folders the series already has in its destinations (S.O.K
   * Server, absent before 1.6), and whether the row waits for a choice. */
  series_folder?: SeriesFolder | null;
  folder_pending?: boolean;
}

/** A folder of the library that already holds a series. */
export interface FolderMatch {
  path: string;
  /** Index of the destination folder that holds it. */
  root: number;
  /** How it was found: by an id, by an earlier rename, by a title. */
  how: "id" | "history" | "title";
  /** The service of the id ("tvdb"), or "nfo" for a tvshow.nfo. */
  source: string | null;
  /** The title its name matched. */
  title: string | null;
  seasons: number[];
  episodes: number;
}

export interface SeriesFolder {
  matches: FolderMatch[];
  /** The match used, "new" for a new folder, null while it waits. */
  chosen: number | "new" | null;
}

/** The status the screens show: a series waiting for the choice of its
 * folder is to pick, though its match is Ready. */
export function statusOf(row: Row): RowStatus {
  return row.folder_pending ? "ambiguous" : row.status;
}

/** The existing folder a row goes into, or null for a new one. */
export function existingFolder(row: Row): FolderMatch | null {
  const found = row.series_folder;
  if (!found || typeof found.chosen !== "number") return null;
  const match = found.matches[found.chosen];
  return match && match.root === row.destination ? match : null;
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
  change: { selected?: number; destination?: number; folder?: number | "new" },
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

/** The format of a file, from its extension: "EPUB", "PDF". */
export function formatOf(file: RowFile): string {
  const found = file.name.match(/\.([a-z0-9]+)$/i);
  return found ? found[1].toUpperCase() : "";
}

/** The console of a game, the first folder of its new name ("Super
 * Nintendo"), or null. */
export function platformOf(row: Row): string | null {
  const parts = row.files[0]?.new_name?.split("/") ?? [];
  return parts.length > 1 ? parts[0] : null;
}

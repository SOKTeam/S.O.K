// The demo of the website: S.O.K Server written in TypeScript, in the
// browser. It answers the routes of /api and sends their events from the
// answers of a real server (data.json, made by scripts/record_demo.py), and
// changes nothing on any disk. Loading the page again starts it again.

import { ApiError, type Events } from "../lib/api";
import { pickLanguage } from "../lib/format";
import type { Operation, ProcessedFile, UndoReport } from "../lib/history";
import type { Rename } from "../lib/renames.svelte";
import type { Row } from "../lib/rows";
import type { Counts, Scan, Summary, ToCheck } from "../lib/scan.svelte";
import type { SettingsChange, SettingsData } from "../lib/settings.svelte";
import type { WatchStatus } from "../lib/watch.svelte";
import data from "./data.json";

/** The new names of the files of a row, for each of its candidates. */
type Names = Record<string, { new_names: (string | null)[]; episodes_found: number | null }>;

/** A row of a recording, before the visit changes it. */
interface Recorded {
  row: Row;
  names: Names;
}

const MEDIA_TYPES = ["movies", "tv", "music", "books", "games"];
const MEDIA_TYPE_OF_KIND: Record<string, string> = {
  movie: "movies",
  episode: "tv",
  album: "music",
  track: "music",
  book: "books",
  game: "games",
};
/** The kind of an operation of the history, for each media type. */
const OPERATION_KIND: Record<string, string> = {
  movies: "movie",
  tv: "tv_series",
  music: "album",
  books: "book",
  games: "game",
};
/** When the file of the automatic sorting arrives, after the page opens. */
const ARRIVAL_MS = 40_000;

// ------------------------------------------------------------- Dates

const opened = Date.now();

/** An "ago" of data.json (seconds before the visit) as a date. */
function before(seconds: number): Date {
  return new Date(opened - seconds * 1000);
}

/** A date as the server writes the times of its jobs: UTC. */
function utc(date: Date): string {
  return date.toISOString().replace(/\.\d{3}Z$/, "+00:00");
}

/** A date as the history writes it: local time, without a zone. */
function local(date: Date): string {
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 19);
}

const clone = <T>(value: T): T => structuredClone(value);
const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// ------------------------------------------------------------- State

const LANGUAGES = data.settings.languages;
let language = pickLanguage(navigator.languages, LANGUAGES) ?? "en";
let loggedIn = true;

const settings = clone(data.settings) as unknown as SettingsData;
settings.settings.language = language;

const watch: WatchStatus = {
  enabled: data.watch.enabled,
  minutes: data.watch.minutes,
  last_check: utc(before(data.watch.last_check)),
  last_run: {
    ...data.watch.last_run,
    date: utc(before(data.watch.last_run.date)),
  },
};

const history: Operation[] = (clone(data.history) as unknown as Operation[]).map((op) => ({
  ...op,
  date: local(before(op.date as unknown as number)),
}));
const processed: ProcessedFile[] = (clone(data.processed) as unknown as ProcessedFile[]).map(
  (file) => ({ ...file, date: local(before(file.date as unknown as number)) }),
);
const sizes: Record<string, number> = { ...data.sizes };

/** Every row the downloads folder can give, as the recording found it. */
const recorded: Recorded[] = [];
for (const type of MEDIA_TYPES) {
  for (const row of (data.rows as unknown as Record<string, Row[]>)[type]) {
    recorded.push({ row, names: (data.names as unknown as Record<string, Names>)[row.id] });
  }
}
const searches = data.searches as unknown as {
  row: number;
  query: string;
  found: Row;
  names: Names;
}[];
const confirmable = data.to_check_rows as unknown as {
  path: string;
  kind: string;
  row: Row;
  names: Names;
}[];
const arriving = data.arriving as unknown as Row;
let arrived = false;

/** The rows of the last analysis, and the names of their candidates. */
let rows: Row[] = [];
const names = new Map<number, Names>();
let toCheck: ToCheck[] = [];
/** The types given to the files to check: the next analyses keep them. */
const choices = new Map<string, string>();
let scan: Scan = {
  ...(clone(data.summary.scan) as unknown as Scan),
  started: utc(before(data.summary.scan.started)),
  finished: utc(before(data.summary.scan.finished)),
};
let rename: Rename | null = null;
let nextId = 1000;

/** The files the next analysis leaves out: renamed, and not undone. */
function isProcessed(path: string): boolean {
  return processed.some((file) => file.path === path);
}

/** What an analysis finds: the rows of the recording whose files wait. */
function analyze(): void {
  rows = [];
  names.clear();
  const found: Recorded[] = [...recorded];
  if (arrived) {
    found.push({ row: arriving, names: {} });
  }
  for (const { row, names: picks } of found) {
    const files = row.files.filter((file) => !isProcessed(file.path));
    if (files.length) {
      rows.push({ ...clone(row), files: clone(files) });
      names.set(row.id, picks);
    }
  }
  toCheck = [];
  for (const item of clone(data.summary.to_check) as ToCheck[]) {
    const kind = choices.get(item.path);
    if (isProcessed(item.path)) continue;
    if (kind) {
      addChosen(item.path, kind);
    } else {
      toCheck.push(item);
    }
  }
}

/** A file to check, given its type: a row of that type, searched. */
function addChosen(path: string, kind: string): void {
  const known = confirmable.find((one) => one.path === path && one.kind === kind);
  const name = path.split("/").pop()!;
  const row: Row = known
    ? clone(known.row)
    : {
        id: nextId++,
        media_type: MEDIA_TYPE_OF_KIND[kind],
        kind,
        title: null,
        query: name.replace(/\.[^.]+$/, ""),
        year: null,
        status: "missing",
        selected: null,
        destination: 0,
        candidates: [],
        files: [{ path, name, new_name: null, error: null }],
        episodes_found: null,
      };
  rows.push(row);
  names.set(row.id, known?.names ?? {});
}

analyze();

function counts(): Record<string, Counts> {
  const all: Record<string, Counts> = {};
  for (const type of MEDIA_TYPES) {
    const own = rows.filter((row) => row.media_type === type);
    all[type] = {
      pending: 0,
      ok: own.filter((row) => row.status === "ok").length,
      ambiguous: own.filter((row) => row.status === "ambiguous").length,
      missing: own.filter((row) => row.status === "missing").length,
      total: own.length,
    };
  }
  return all;
}

function summary(): Summary {
  return { scan: clone(scan), counts: counts(), to_check: clone(toCheck) };
}

// ------------------------------------------------------------- Events

const sources = new Set<DemoEvents>();

class DemoEvents implements Events {
  private listeners = new Map<string, ((event: Event) => void)[]>();

  addEventListener(type: string, listener: (event: Event) => void): void {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
  }

  close(): void {
    sources.delete(this);
  }

  send(type: string, payload: object): void {
    const event = new MessageEvent(type, { data: JSON.stringify({ type, ...payload }) });
    for (const listener of this.listeners.get(type) ?? []) {
      listener(event);
    }
  }
}

function publish(type: string, payload: object): void {
  for (const source of sources) {
    source.send(type, payload);
  }
}

/** GET /api/events: the summary first, then the events as they happen. */
export function demoEvents(): Events {
  const source = new DemoEvents();
  sources.add(source);
  setTimeout(() => source.send("scan", summary()), 0);
  return source;
}

// ------------------------------------------------------------- Jobs

const busy = () => scan.status === "running" || rename?.status === "running";

/** An analysis of the downloads folder: detect, then search, as the server. */
async function runScan(auto: boolean, find: () => void): Promise<void> {
  scan = {
    id: scan.id + 1,
    status: "running",
    started: utc(new Date()),
    finished: null,
    error: null,
    missing_sources: [],
    processed: processed.length,
    auto,
    progress: null,
  };
  publish("scan", summary());
  publish("progress", { phase: "detect", done: 0, total: 0 });
  await wait(900);
  find();
  const pending = rows.length;
  publish("progress", { phase: "search", done: 0, total: pending });
  for (let done = 1; done <= pending; done++) {
    await wait(Math.max(60, 1600 / Math.max(pending, 1)));
    publish("progress", { phase: "search", done, total: pending });
  }
  scan = { ...scan, status: "done", finished: utc(new Date()) };
  publish("scan", summary());
}

/** The new path of a file under the destination of its row. */
function destinationOf(row: Row): string {
  const folders = settings.folders[row.media_type];
  return folders[row.destination < folders.length ? row.destination : 0];
}

/** The subtitles that follow a video: same name, then a language. */
function subtitlesOf(path: string): string[] {
  const stem = path.replace(/\.[^./]+$/, "");
  return Object.keys(sizes).filter(
    (other) => other !== path && other.startsWith(`${stem}.`) && other.endsWith(".srt"),
  );
}

/** Rename rows: an operation of the history, the files processed. */
async function runRename(mediaType: string, chosen: Row[], auto: boolean): Promise<void> {
  const mode = settings.settings.file_mode as Operation["files"][number]["mode"];
  const moves: { source: string; target: string; follows: string | null }[] = [];
  for (const row of chosen) {
    const root = destinationOf(row);
    for (const file of row.files) {
      if (!file.new_name) continue;
      const target = `${root}/${file.new_name}`;
      moves.push({ source: file.path, target, follows: null });
      for (const subtitle of subtitlesOf(file.path)) {
        const suffix = subtitle.slice(file.path.replace(/\.[^./]+$/, "").length);
        moves.push({
          source: subtitle,
          target: target.replace(/\.[^./]+$/, "") + suffix,
          follows: target,
        });
      }
    }
  }
  rename = {
    id: nextId++,
    media_type: mediaType,
    status: "running",
    started: utc(new Date()),
    finished: null,
    auto,
    error: null,
    result: null,
    progress: { done: 0, total: moves.length },
  };
  publish("rename", { rename: clone(rename) });
  for (let done = 1; done <= moves.length; done++) {
    await wait(120);
    publish("progress", { phase: "rename", done, total: moves.length });
  }
  const operation: Operation = {
    id: crypto.randomUUID().replaceAll("-", ""),
    date: local(new Date()),
    kind: OPERATION_KIND[mediaType],
    media_type: mediaType,
    undone: false,
    partly_undone: false,
    auto,
    files: moves.map((move, index) => ({ index, ...move, mode, undone: false })),
  };
  history.unshift(operation);
  for (const move of moves) {
    processed.unshift({
      path: move.source,
      target: move.target,
      size: sizes[move.source] ?? 0,
      date: operation.date,
      operation: operation.id,
    });
  }
  const done = new Set(chosen.map((row) => row.id));
  rows = rows.filter((row) => !done.has(row.id));
  const subtitles = moves.filter((move) => move.follows).length;
  rename = {
    ...rename,
    status: "done",
    finished: utc(new Date()),
    progress: null,
    result: {
      renamed: moves.length - subtitles,
      subtitles,
      skipped: [],
      errors: [],
      operation: operation.id,
    },
  };
  publish("rename", { rename: clone(rename) });
}

/** The automatic sorting: a look at the folders at each interval, and the
 * file that arrives during the visit, sorted with no click. */
function startWatch(): void {
  setTimeout(async () => {
    if (!watch.enabled || arrived) return;
    if (busy()) return startWatch();
    arrived = true;
    sizes[arriving.files[0].path] = 9100 * 1024 ** 2;
    watch.last_check = utc(new Date());
    publish("watch", clone(watch));
    await runScan(true, () => {
      rows.push(clone(arriving));
      names.set(arriving.id, {});
    });
    const ready = rows.filter((row) => row.id === arriving.id && row.status === "ok");
    if (ready.length) {
      await runRename("movies", ready, true);
    }
    watch.last_run = {
      date: utc(new Date()),
      scan: scan.id,
      renamed: ready.length,
      errors: [],
    };
    publish("watch", clone(watch));
  }, ARRIVAL_MS);
}

startWatch();
setInterval(() => {
  if (watch.enabled) {
    watch.last_check = utc(new Date());
    publish("watch", clone(watch));
  }
}, 60_000);

// ------------------------------------------------------------- Rows

function rowOf(id: number): Row {
  const row = rows.find((one) => one.id === id);
  if (!row) throw new ApiError(404, "unknown_row");
  return row;
}

/** Pick a candidate: the row is Ready, its files get the names of it. */
function pick(row: Row, index: number): void {
  const picked = names.get(row.id)?.[String(index)];
  row.selected = index;
  row.status = "ok";
  if (picked) {
    row.files.forEach((file, i) => (file.new_name = picked.new_names[i] ?? null));
    row.episodes_found = picked.episodes_found;
  }
}

const normal = (text: string) =>
  text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();

/** Search a row again: the searches of the recording, else nothing found. */
function search(row: Row, query: string): void {
  const wanted = normal(query);
  const original = recorded.find((one) => one.row.id === row.id);
  const known = searches.find((one) => one.row === row.id && normal(one.query) === wanted);
  let found: Row | undefined;
  let picks: Names = {};
  if (known) {
    found = known.found;
    picks = known.names;
  } else if (original && normal(original.row.query ?? "") === wanted) {
    found = original.row;
    picks = original.names;
  }
  row.query = query;
  names.set(row.id, picks);
  if (!found) {
    Object.assign(row, { status: "missing", selected: null, candidates: [], episodes_found: null });
    row.files.forEach((file) => (file.new_name = null));
    return;
  }
  Object.assign(row, {
    status: found.status,
    selected: found.selected,
    candidates: clone(found.candidates),
    episodes_found: found.episodes_found,
  });
  row.files.forEach((file) => {
    file.new_name = found.files.find((one) => one.path === file.path)?.new_name ?? null;
  });
}

// ------------------------------------------------------------- Settings

const FOLDERS = ["config", "downloads", "media"];
const MEDIA_FOLDERS = ["Books", "Games", "Movies", "Movies 4K", "Music", "TV Shows"];

/** GET /api/settings/browse: the folders of a made-up container. */
function browse(path = "/"): object {
  const clean = path.replace(/\/+$/, "") || "/";
  const names = clean === "/" ? FOLDERS : clean === "/media" ? MEDIA_FOLDERS : [];
  const parent = clean === "/" ? null : clean.replace(/\/[^/]+$/, "") || "/";
  return {
    path: clean,
    parent,
    folders: names.map((name) => ({ name, path: `${clean === "/" ? "" : clean}/${name}` })),
  };
}

function changeSettings(change: SettingsChange): SettingsData {
  for (const folders of Object.values(change.folders ?? {})) {
    const wrong = folders.find((folder) => !folder.startsWith("/"));
    if (wrong) throw new ApiError(422, { code: "invalid_folder", item: wrong });
  }
  for (const [name, value] of Object.entries(change.settings ?? {})) {
    settings.settings[name] = value;
  }
  if (change.settings && "language" in change.settings) {
    language = String(change.settings.language);
  }
  for (const [name, value] of Object.entries(change.keys ?? {})) {
    for (const service of settings.keys) {
      for (const key of service.keys) {
        if (key.key === name) key.set = value.trim() !== "";
      }
    }
  }
  for (const [type, folders] of Object.entries(change.folders ?? {})) {
    settings.folders[type] = folders;
  }
  if (change.folders) {
    settings.link_checks = settings.folders.sources.flatMap((source) =>
      MEDIA_TYPES.flatMap((type) =>
        settings.folders[type].map((destination) => ({
          source,
          destination,
          ok: true,
          problem: null,
          tested: true,
        })),
      ),
    );
  }
  const notify = settings.notifications;
  for (const [name, value] of Object.entries(change.notifications ?? {})) {
    const set = value.trim() !== "";
    if (name === "discord_url") notify.discord.set = set;
    if (name === "webhook_url") notify.webhook.set = set;
    if (name === "jellyfin_url") notify.jellyfin.url = value.trim().replace(/\/$/, "");
    if (name === "plex_url") notify.plex.url = value.trim().replace(/\/$/, "");
    if (name === "jellyfin_key") notify.jellyfin.set = set;
    if (name === "plex_token") notify.plex.set = set;
  }
  if (
    change.settings &&
    ("auto_sort" in change.settings || "auto_sort_minutes" in change.settings)
  ) {
    watch.enabled = Boolean(settings.settings.auto_sort);
    watch.minutes = Number(settings.settings.auto_sort_minutes);
    publish("watch", clone(watch));
    if (watch.enabled) startWatch();
  }
  return clone(settings);
}

// ------------------------------------------------------------- Routes

type Body = Record<string, unknown>;

/** The texts of a language: the translation files of S.O.K. */
const TEXTS = import.meta.glob<{ default: Record<string, string> }>(
  "../../../src/sok/resources/i18n/*.json",
);

async function texts(wanted: string | null): Promise<object> {
  const chosen = wanted && LANGUAGES.includes(wanted) ? wanted : language;
  const file = TEXTS[`../../../src/sok/resources/i18n/${chosen}.json`];
  return { language: chosen, languages: LANGUAGES, texts: (await file()).default };
}

async function answer(method: string, path: string, query: URLSearchParams, body: Body) {
  const route = `${method} ${path}`;
  switch (route) {
    case "GET /api/session":
      return {
        auth: "login",
        account: true,
        logged_in: loggedIn,
        username: "demo",
        language,
      };
    case "POST /api/login":
      loggedIn = true;
      return { username: "demo" };
    case "POST /api/logout":
      loggedIn = false;
      return undefined;
    case "GET /api/i18n":
      return texts(query.get("lang"));
    case "GET /api/scans/current":
      return summary();
    case "POST /api/scans": {
      if (busy()) throw new ApiError(409, "already_running");
      if (!settings.folders.sources.length) throw new ApiError(409, "no_sources");
      runScan(false, analyze);
      return { id: scan.id + 1 };
    }
    case "POST /api/to-check": {
      const { path: file, kind } = body as { path: string; kind: string };
      toCheck = toCheck.filter((item) => item.path !== file);
      choices.set(file, kind);
      addChosen(file, kind);
      return summary();
    }
    case "GET /api/rows":
      return { rows: clone(rows.filter((row) => row.media_type === query.get("type"))) };
    case "GET /api/renames/current":
      return { rename: clone(rename) };
    case "POST /api/renames": {
      const { type, rows: ids } = body as { type: string; rows?: number[] };
      if (busy()) throw new ApiError(409, "already_running");
      const chosen = rows.filter(
        (row) => row.media_type === type && row.status === "ok" && (!ids || ids.includes(row.id)),
      );
      if (!chosen.length) throw new ApiError(409, "nothing_to_rename");
      if (!settings.folders[type].length) throw new ApiError(409, "no_destination");
      runRename(type, chosen, false);
      await wait(0);
      return { id: rename!.id };
    }
    case "GET /api/history":
      return { operations: clone(history) };
    case "GET /api/processed":
      return { files: clone(processed) };
    case "POST /api/processed/forget": {
      const { paths } = body as { paths: string[] };
      const before = processed.length;
      for (let i = processed.length - 1; i >= 0; i--) {
        if (paths.includes(processed[i].path)) processed.splice(i, 1);
      }
      return { forgotten: before - processed.length };
    }
    case "GET /api/settings":
      return clone(settings);
    case "PATCH /api/settings":
      return changeSettings(body as SettingsChange);
    case "GET /api/settings/browse":
      return browse(query.get("path") ?? undefined);
    case "POST /api/settings/test-key": {
      const { service } = body as { service: string };
      const keys = settings.keys.find((one) => one.service === service)?.keys ?? [];
      return { service, status: keys.every((key) => key.set) ? "ok" : "missing_key" };
    }
    case "POST /api/settings/test-notification": {
      const { target } = body as { target: keyof SettingsData["notifications"] };
      const value = settings.notifications[target];
      const set = typeof value === "boolean" ? value : value?.set;
      return { ok: Boolean(set), error: set ? null : "not_set" };
    }
    case "POST /api/settings/test-link":
      return { ...(body as object), ok: true, problem: null, tested: true };
    case "GET /api/watch":
      return clone(watch);
  }

  let match = path.match(/^\/api\/rows\/(\d+)(\/search)?$/);
  if (match) {
    const row = rowOf(Number(match[1]));
    if (method === "PATCH") {
      const { selected, destination } = body as { selected?: number; destination?: number };
      if (selected !== undefined && selected !== null) {
        if (!(selected >= 0 && selected < row.candidates.length)) {
          throw new ApiError(422, "invalid_selection");
        }
        pick(row, selected);
      }
      if (destination !== undefined && destination !== null) {
        row.destination = destination;
      }
      return clone(row);
    }
    if (method === "POST" && match[2]) {
      await wait(500);
      search(row, String((body as { query: string }).query));
      return clone(row);
    }
  }

  match = path.match(/^\/api\/history\/(\w+)\/undo$/);
  if (match && method === "POST") {
    if (busy()) throw new ApiError(409, "already_running");
    const operation = history.find((op) => op.id === match![1]);
    if (!operation) throw new ApiError(404, "unknown_operation");
    const index = (body as { index?: number }).index;
    const chosen = operation.files.filter((file) => {
      if (file.undone) return false;
      if (index === undefined || index === null) return true;
      const video = operation.files[index];
      return file.index === index || file.follows === video.target;
    });
    for (const file of chosen) {
      file.undone = true;
      const at = processed.findIndex((one) => one.path === file.source);
      if (at >= 0) processed.splice(at, 1);
    }
    operation.undone = operation.files.every((file) => file.undone);
    operation.partly_undone = !operation.undone && operation.files.some((file) => file.undone);
    const report: UndoReport = {
      restored: chosen.map((file) => file.source),
      skipped: [],
      operation: clone(operation),
    };
    return report;
  }

  throw new ApiError(404, "not_found");
}

/** The answer of a route of /api, as api() of lib/api.ts gives it. */
export async function demoApi<T>(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<T> {
  const url = new URL(path, "http://demo");
  await wait(80);
  const result = await answer(
    options.method ?? "GET",
    url.pathname,
    url.searchParams,
    (options.body ?? {}) as Body,
  );
  return clone(result) as T;
}

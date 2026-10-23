// The text of an error of the API, in the language of the interface.

import { ApiError } from "./api";
import { t } from "./i18n.svelte";
import { MEDIA_PAGES } from "./pages";
import type { WatchProblem } from "./watch.svelte";

export function errorText(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return t("web_error_unknown", "Something went wrong. Try again.");
  }
  switch (error.code) {
    case "offline":
      return t("web_error_offline", "The server does not answer.");
    case "invalid_account":
      return t(
        "web_error_invalid_account",
        "Give a user name, and a password of 8 characters or more.",
      );
    case "wrong_login":
      return t("web_error_wrong_login", "Wrong user name or password.");
    case "invalid_folder":
      return t(
        "web_error_invalid_folder",
        "“{item}” is not a folder the server can see. Give its full path, as mounted in the container.",
        { item: item(error) },
      );
    case "invalid_value":
      return t("web_error_invalid_value", "This value cannot be saved.");
    case "key_locked":
      return t("web_error_key_locked", "An environment variable sets this key: change it there.");
    case "too_many_attempts":
      return t("web_error_too_many_attempts", "Too many attempts. Try again in {seconds} s.", {
        seconds: error.retryAfter ?? 30,
      });
    case "already_running":
      return t("web_error_already_running", "An analysis or a rename is already running.");
    case "rename_running":
      return t("web_error_rename_running", "A rename is running: wait for its end.");
    case "scan_running":
      return t("web_error_scan_running", "An analysis is running: wait for its end.");
    case "unreadable_folder":
      return t("web_error_unreadable_folder", "The server cannot read this folder.");
    case "nothing_to_rename":
      return t("web_error_nothing_to_rename", "No Ready row to rename.");
    case "no_destination":
      return t(
        "web_error_no_destination",
        "Add a destination folder for this type in the settings first.",
      );
    case "different_drives":
    case "no_hard_links":
    case "missing_folder": {
      const detail = error.detail as { source?: string; destination?: string };
      return linkProblemText(error.code, detail.source ?? "", detail.destination ?? "");
    }
    case "no_sources":
      return t("web_error_no_sources", "Add a source folder in the settings first.");
    default:
      return t("web_error_unknown", "Something went wrong. Try again.");
  }
}

// The names of the services, as the settings list them.
const SERVICE_NAMES: Record<string, string> = {
  tmdb: "TMDB",
  tvdb: "TVDB",
  omdb: "OMDb",
  lastfm: "Last.fm",
  spotify: "Spotify",
  deezer: "Deezer",
  musicbrainz: "MusicBrainz",
  google_books: "Google Books",
  openlibrary: "Open Library",
  igdb: "IGDB",
  rawg: "RAWG",
  fanart: "Fanart.tv",
};

export function serviceName(id: string | undefined): string {
  return (id && SERVICE_NAMES[id]) ?? id ?? "";
}

/** Why a search stopped: {"code", "service"} of an analysis or of a 409. */
export function stopText(stop: { code: string; service?: string; message?: string }): string {
  const service = serviceName(stop.service);
  switch (stop.code) {
    case "missing_key":
      return t(
        "web_stop_missing_key",
        "{service}: the key is missing. Add it in the settings, then analyze again.",
        { service },
      );
    case "key_refused":
      return t("web_stop_key_refused", "{service} refused the key: check it in the settings.", {
        service,
      });
    case "rate_limited":
      return t(
        "web_stop_rate_limited",
        "{service}: too many requests, or the quota is used. Try again later.",
        { service },
      );
    default:
      return t("web_stop_failed", "The analysis failed: {message}", {
        message: stop.message ?? stop.code,
      });
  }
}

/** The text of a search of a row stopped by a key (409). */
export function searchErrorText(error: ApiError): string {
  return stopText(error.detail as { code: string; service?: string });
}

/** What a refused setting is about: {"code", "item"} of "detail". */
function item(error: ApiError): string {
  return String((error.detail as { item?: string } | null)?.item ?? "");
}

/** Why a hard link cannot be made from a folder to another. */
export function linkProblemText(problem: string, source: string, destination: string): string {
  const values = { source, destination };
  switch (problem) {
    case "different_drives":
      return t(
        "web_link_different_drives",
        "“{source}” and “{destination}” are on two drives, or two Docker mounts: mount their common parent folder once.",
        values,
      );
    case "no_hard_links":
      return t(
        "web_link_no_hard_links",
        "The disk of “{destination}” has no hard links (FAT, exFAT, most network shares).",
        values,
      );
    default:
      return t("web_link_missing_folder", "“{source}” or “{destination}” is missing.", values);
  }
}

/** What to change so that a hard link works. */
export function linkFixText(problem: string): string {
  switch (problem) {
    case "different_drives":
      return t(
        "web_link_fix_different_drives",
        "mount the folder that holds both of them once in the container (for example /mnt/storage:/data), then choose them under /data. On two real disks, choose a destination on the disk of the downloads.",
      );
    case "no_hard_links":
      return t(
        "web_link_fix_no_hard_links",
        "choose a destination on a disk that has hard links (ext4, Btrfs, XFS, ZFS, NTFS, APFS), or the Copy mode.",
      );
    default:
      return t(
        "web_link_fix_missing_folder",
        "check that the folder still exists, and that it is mounted in the container.",
      );
  }
}

/** The text of a problem of an automatic sorting: the stop of its analysis,
 * or the refused rename of a tab, named first. */
export function watchProblemText(problem: WatchProblem): string {
  if (!problem.media_type) {
    return problem.code === "already_running" ||
      problem.code === "rename_running" ||
      problem.code === "no_sources"
      ? errorText(new ApiError(409, problem.code))
      : stopText(problem);
  }
  const page = MEDIA_PAGES.find((p) => p.mediaType === problem.media_type);
  const tab = page ? t(page.key, page.english) : problem.media_type;
  const text =
    problem.code === "failed"
      ? t("web_rename_failed", "The rename failed: {message}", {
          message: problem.message ?? problem.code,
        })
      : errorText(new ApiError(409, problem));
  return t("web_watch_problem", "{tab}: {text}", { tab, text });
}

// The live preview of the settings: an example file of a type, the name it
// has, and the path it would get with a name model, the parts filled by
// S.O.K marked. As the preview of the desktop app
// (src/sok/ui/components/settings/preview.py), with fill_format and
// format_name of src/sok/core/utils.py, and the folders the server adds
// (search.py new_names).

/** The setting of the model of each media type. */
export const FORMAT_KEYS: Record<string, string> = {
  movies: "movie_format",
  tv: "video_format",
  music: "music_format",
  books: "book_format",
  games: "game_format",
};

/** The colors of the stand-in poster of each example, and of its light. */
export const EXAMPLE_COLORS: Record<string, [string, string]> = {
  movies: ["#9fae55", "#2c3410"],
  tv: ["#5f8fb0", "#14273a"],
  music: ["#c0607e", "#3a1220"],
  books: ["#c99a5b", "#3d2a12"],
  games: ["#5fae9d", "#0f3029"],
};
export const EXAMPLE_LIGHTS: Record<string, string> = {
  movies: "150, 170, 80",
  tv: "95, 143, 176",
  music: "192, 96, 126",
  books: "201, 154, 91",
  games: "95, 174, 157",
};

// Marks around a filled value.
const OPEN = "\x01";
const CLOSE = "\x02";
const filled = (value: string) => `${OPEN}${value}${CLOSE}`;

interface Example {
  title: string;
  year: string;
  /** The name it has in the downloads. */
  before: string;
  values: Record<string, string>;
  extension: string;
  /** Music: a "/" of the model makes folders. */
  foldersInModel?: boolean;
  /** The folders before the name; "{season}" is the word of the language. */
  folders?: string[];
}

export const EXAMPLES: Record<string, Example> = {
  movies: {
    title: "Oppenheimer",
    year: "2023",
    before: "oppenheimer.2023.2160p.mkv",
    values: { title: "Oppenheimer", year: "2023", quality: "2160p" },
    extension: ".mkv",
  },
  tv: {
    title: "Severance",
    year: "2022",
    before: "severance.s02e01.1080p.mkv",
    values: {
      title: "Severance",
      season: "02",
      episode: "01",
      episode_title: "Hello, Ms. Cobel",
      season_num: "2",
      episode_num: "1",
    },
    extension: ".mkv",
    folders: [filled("Severance"), `{season} ${filled("2")}`],
  },
  music: {
    title: "Discovery",
    year: "2001",
    before: "01 one more time.flac",
    values: {
      artist: "Daft Punk",
      album: "Discovery",
      track: "01",
      title: "One More Time",
      year: "2001",
    },
    extension: ".flac",
    foldersInModel: true,
  },
  books: {
    title: "Dune",
    year: "1965",
    before: "dune_frank_herbert.epub",
    values: { author: "Frank Herbert", title: "Dune", year: "1965" },
    extension: ".epub",
    folders: [filled("Frank Herbert")],
  },
  games: {
    title: "Celeste",
    year: "2018",
    before: "Celeste (Europe).nsp",
    values: { title: "Celeste", year: "2018", platform: "Nintendo Switch", tags: "(Europe)" },
    extension: ".nsp",
    folders: [filled("Nintendo Switch")],
  },
};

/**
 * Fill a name model as fill_format does: an unknown or empty value is left
 * out with what it leaves around it; "" for a model that is not valid ("{",
 * "{0}").
 */
export function fillFormat(model: string, values: Record<string, string>): string {
  let valid = true;
  let text = model.replace(/\{\{|\}\}|\{([^{}]*)\}|[{}]/g, (whole, field?: string) => {
    if (whole === "{{") return "{";
    if (whole === "}}") return "}";
    if (field === undefined) {
      valid = false;
      return "";
    }
    const name = field.split(/[!:]/)[0];
    // No positional value, and no attribute of a value.
    if (!name || /^\d/.test(name) || /[.[]/.test(name)) {
      valid = false;
      return "";
    }
    return values[name] ?? "";
  });
  if (!valid) return "";
  text = text.replace(/\(\s*\)|\[\s*\]/g, "");
  text = text.replace(/\s*-\s*(?:-\s*)+/g, " - ");
  text = text.replace(/^[\s\-_.]+|[\s\-_.]+$/g, "");
  return text.replace(/\s{2,}/g, " ");
}

/** A file or folder name as format_name makes it. */
export function formatName(name: string): string {
  let text = name.replace(/[<>:"/\\|?*]/g, "").replace(/ +/g, " ");
  text = text.replace(/[ .]+(\.[A-Za-z0-9]{1,5})$/, "$1");
  return text.replace(/[ .]+$/, "");
}

/** A part of a path: filled by S.O.K (accent) or not. */
export interface Piece {
  text: string;
  filled: boolean;
}

function pieces(text: string): Piece[] {
  const out: Piece[] = [];
  for (const [i, part] of text.split(new RegExp(`[${OPEN}${CLOSE}]`)).entries()) {
    if (part) out.push({ text: part, filled: i % 2 === 1 });
  }
  return out;
}

/**
 * The path the example of a media type gets with a model, under its
 * destination; null when the model gives no name.
 *
 * @param season The word of the language for the season folders.
 */
export function previewPath(
  mediaType: string,
  model: string,
  destination: string,
  season: string,
): Piece[] | null {
  const example = EXAMPLES[mediaType];
  const marked = Object.fromEntries(
    Object.entries(example.values).map(([key, value]) => [key, filled(value)]),
  );
  const parts = (example.foldersInModel ? model.split("/") : [model])
    .map((part) => formatName(fillFormat(part, marked)))
    .filter((part) => part.replace(new RegExp(`[${OPEN}${CLOSE}]`, "g"), "").trim());
  if (!parts.length) return null;
  parts[parts.length - 1] += example.extension;
  const folders = (example.folders ?? []).map((folder) => folder.replace("{season}", season));
  const root = destination.replace(/\/+$/, "");
  return pieces([root, ...folders, ...parts].join("/"));
}

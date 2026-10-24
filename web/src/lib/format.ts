// Pure helpers, tested without a browser.

/** Put the values in the {placeholders} of a text: "{n} files". */
export function fill(text: string, values: Record<string, string | number> = {}): string {
  return text.replace(/\{(\w+)\}/g, (whole, name: string) =>
    name in values ? String(values[name]) : whole,
  );
}

/** The language of the browser that S.O.K has, else null: "fr-CA" → "fr". */
export function pickLanguage(
  wanted: readonly string[],
  available: readonly string[],
): string | null {
  for (const tag of wanted) {
    const code = tag.toLowerCase().split("-")[0];
    if (available.includes(code)) {
      return code;
    }
  }
  return null;
}

/** The folder that holds a path: "/data/movies" → "/data", "/data" → "/". */
export function parentFolder(path: string): string {
  return path.replace(/\/[^/]+\/?$/, "") || "/";
}

/** A new name split into its folders and its file: "Show/Season 1/x.mkv" →
 * { folder: "Show/Season 1", name: "x.mkv" }. */
export function splitName(path: string): { folder: string; name: string } {
  const cut = path.lastIndexOf("/");
  return cut < 0
    ? { folder: "", name: path }
    : { folder: path.slice(0, cut), name: path.slice(cut + 1) };
}

/** The day of a date, as a key to group by: "2026-10-24". */
export function dayKey(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** Whole days from a day to today: 0 today, 1 yesterday. */
export function daysAgo(date: Date, today: Date): number {
  const start = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  return Math.round((start(today) - start(date)) / 86_400_000);
}

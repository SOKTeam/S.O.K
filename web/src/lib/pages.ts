// The pages of the sidebar, in order.

export interface Page {
  path: string;
  /** Key and English text of its name. */
  key: string;
  english: string;
  icon: string;
  /** The tab of a media type (movies, tv…), for its counts. */
  mediaType?: string;
}

export const ANALYSIS: Page = { path: "/", key: "web_analysis", english: "Analysis", icon: "home" };

export const MEDIA_PAGES: Page[] = [
  { path: "/movies", key: "movies", english: "Movies", icon: "video", mediaType: "movies" },
  { path: "/tv", key: "tv_shows", english: "TV Shows", icon: "tv", mediaType: "tv" },
  { path: "/music", key: "music", english: "Music", icon: "music", mediaType: "music" },
  { path: "/books", key: "books", english: "Books", icon: "book", mediaType: "books" },
  { path: "/games", key: "games", english: "Games", icon: "game", mediaType: "games" },
];

export const OTHER_PAGES: Page[] = [
  { path: "/history", key: "history", english: "History", icon: "history" },
  { path: "/settings", key: "settings", english: "Settings", icon: "settings" },
];

export const PAGES = [ANALYSIS, ...MEDIA_PAGES, ...OTHER_PAGES];

/** The page of a path; the analysis for an unknown one. A page can have
 * sub-pages: /history/processed is the history. */
export function pageOf(path: string): Page {
  return (
    PAGES.find((page) => page.path === path) ??
    PAGES.find((page) => page.path !== "/" && path.startsWith(`${page.path}/`)) ??
    ANALYSIS
  );
}

// The page shown is the path of the address: /movies, /settings…, under the
// base of the build ("/", or "/demo/" for the demo on the website).
// Going to another page plays a short transition (app.css, "page"): the old
// page fades out, the new one fades in rising a little; the nav stays still.

import { flushSync } from "svelte";

const BASE = import.meta.env.BASE_URL.replace(/\/$/, "");

/** The path of a page in an address: "/demo/movies" is "/movies". */
function pathOf(pathname: string): string {
  const path = pathname.startsWith(BASE) ? pathname.slice(BASE.length) : pathname;
  return path || "/";
}

const state = $state({ path: pathOf(location.pathname) });

/** The page of a path: "/settings/auto" is still the Settings. */
const pageKey = (path: string) => path.split("/")[1] ?? "";

const still = matchMedia("(prefers-reduced-motion: reduce)");

/** Show a path, with the transition when it is another page. */
function show(path: string, animate = true): void {
  if (
    !animate ||
    still.matches ||
    pageKey(path) === pageKey(state.path) ||
    !document.startViewTransition
  ) {
    state.path = path;
    return;
  }
  document.startViewTransition(async () => {
    holds = [];
    state.path = path;
    flushSync();
    const waits = holds;
    holds = null;
    // The old page stays on screen while the new one reads its rows and
    // its first pictures: the fade then goes to the finished page, not to a
    // page still filling (the movies drawn in the grid of the music).
    if (waits.length) await Promise.race([Promise.all(waits), wait(HOLD_MS)]);
  });
}

/** How long a page may keep the old one on screen, at most. */
const HOLD_MS = 300;

// The pages that asked to be waited for, while a transition starts.
let holds: Promise<void>[] | null = null;

const wait = (ms: number) => new Promise<void>((done) => setTimeout(done, ms));

/** Called by a page as it starts showing (an effect): during a transition,
 * the fade waits until the release returned is called. Outside a
 * transition the release does nothing. */
export function hold(): () => void {
  if (!holds) return () => {};
  let release = () => {};
  holds.push(new Promise<void>((done) => (release = done)));
  return release;
}

/** Wait until these pictures are loaded and decoded (failures are fine). */
export function decoded(urls: (string | null)[]): Promise<void> {
  return Promise.all(
    urls.filter(Boolean).map((url) => {
      const image = new Image();
      image.src = url!;
      return image.decode().catch(() => {});
    }),
  ).then(() => {});
}

window.addEventListener("popstate", (event) => {
  // A swipe back of the browser already moves the page: no second motion.
  const swiped = (event as PopStateEvent & { hasUAVisualTransition?: boolean })
    .hasUAVisualTransition;
  show(pathOf(location.pathname), !swiped);
});

export const router = {
  get path() {
    return state.path;
  },
};

/** The address of a page, for href. */
export function href(path: string): string {
  return BASE + path;
}

/** Show another page, as a link does. */
export function navigate(path: string): void {
  if (path !== state.path) {
    history.pushState(null, "", href(path));
    show(path);
  }
}

/** Change the address without a new step in the history: the Settings
 * follow the block read (/settings/auto). */
export function replace(path: string): void {
  if (path !== state.path) {
    history.replaceState(null, "", href(path));
    state.path = path;
  }
}

/** onclick of a link: navigate without loading the page again, unless the
 * user opens it elsewhere (Cmd/Ctrl click, middle button). */
export function follow(event: MouseEvent): void {
  const link = event.currentTarget as HTMLAnchorElement;
  if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
    return;
  }
  event.preventDefault();
  navigate(pathOf(link.pathname));
}

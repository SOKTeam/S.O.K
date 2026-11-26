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
  document.startViewTransition(() => {
    state.path = path;
    flushSync();
  });
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

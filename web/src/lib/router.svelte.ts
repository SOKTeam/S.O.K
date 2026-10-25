// The page shown is the path of the address: /movies, /settings…, under the
// base of the build ("/", or "/demo/" for the demo on the website).

const BASE = import.meta.env.BASE_URL.replace(/\/$/, "");

/** The path of a page in an address: "/demo/movies" is "/movies". */
function pathOf(pathname: string): string {
  const path = pathname.startsWith(BASE) ? pathname.slice(BASE.length) : pathname;
  return path || "/";
}

const state = $state({ path: pathOf(location.pathname) });

window.addEventListener("popstate", () => {
  state.path = pathOf(location.pathname);
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

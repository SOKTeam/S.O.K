// The page shown is the path of the address: /movies, /settings…

const state = $state({ path: location.pathname });

window.addEventListener("popstate", () => {
  state.path = location.pathname;
});

export const router = {
  get path() {
    return state.path;
  },
};

/** Show another page, as a link does. */
export function navigate(path: string): void {
  if (path !== state.path) {
    history.pushState(null, "", path);
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
  navigate(link.pathname);
}

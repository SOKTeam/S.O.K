// The light of the scene: a halo of the color of the poster shown, painted
// by the window behind the navigation, the list and the scene (as the
// LightColumn of the desktop app). A screen sets it; null puts it out.

const state = $state<{ color: string | null }>({ color: null });

export const light = {
  /** "r, g, b", or null. */
  get color() {
    return state.color;
  },
};

export function setLight(color: string | null): void {
  state.color = color;
}

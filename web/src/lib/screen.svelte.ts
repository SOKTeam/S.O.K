// The width of the window, for what CSS alone cannot do: under 1000px the
// scene slides over the list (as the desktop app), under 700px the phone
// (the menu, the docked keys, the sheets).

export const NARROW = 999;
export const PHONE = 699;

const state = $state({ narrow: false, phone: false });

export const screen = {
  /** Under 1000px: the scene slides over the list. */
  get narrow() {
    return state.narrow;
  },
  /** Under 700px: a phone. */
  get phone() {
    return state.phone;
  },
};

/** Follow the width of the window. */
export function startScreen(): void {
  const narrow = matchMedia(`(max-width: ${NARROW}px)`);
  const phone = matchMedia(`(max-width: ${PHONE}px)`);
  const read = () => {
    state.narrow = narrow.matches;
    state.phone = phone.matches;
  };
  read();
  narrow.addEventListener("change", read);
  phone.addEventListener("change", read);
}

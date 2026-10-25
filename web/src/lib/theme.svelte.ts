// The theme of the interface, chosen in each browser: the light theme of
// macOS (white and gray), the orange one of Windows and Linux, the dark one,
// or the one of the system, as the desktop app does.

export type Theme = "light" | "orange" | "dark";
export type ThemeChoice = Theme | "system";

export const THEME_CHOICES: ThemeChoice[] = ["system", "light", "orange", "dark"];

const STORAGE_KEY = "sok-theme";

/**
 * The theme shown for a choice: the system one is dark in dark mode, else
 * white on a Mac and orange elsewhere.
 */
export function resolveTheme(choice: ThemeChoice, dark: boolean, mac: boolean): Theme {
  if (choice !== "system") return choice;
  if (dark) return "dark";
  return mac ? "light" : "orange";
}

function readChoice(): ThemeChoice {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (THEME_CHOICES.includes(saved as ThemeChoice)) return saved as ThemeChoice;
  } catch {
    // No storage (private window): the system theme.
  }
  return "system";
}

// Read from the browser by startTheme().
const state = $state({ choice: "system" as ThemeChoice, dark: false, mac: false });

export const theme = {
  get choice() {
    return state.choice;
  },
  get current(): Theme {
    return resolveTheme(state.choice, state.dark, state.mac);
  },
};

function apply(): void {
  document.documentElement.dataset.theme = theme.current;
}

/** Keep the theme of the page in step with the choice and the system. */
export function startTheme(): void {
  const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");
  state.choice = readChoice();
  state.dark = darkQuery.matches;
  state.mac = /Mac/.test(navigator.platform || navigator.userAgent);
  apply();
  darkQuery.addEventListener("change", (event) => {
    state.dark = event.matches;
    apply();
  });
}

export function chooseTheme(choice: ThemeChoice): void {
  state.choice = choice;
  try {
    localStorage.setItem(STORAGE_KEY, choice);
  } catch {
    // Kept for this visit only.
  }
  apply();
}

// The theme of the interface, chosen in each browser: dark (the default of
// the art direction), light, or the one of the system.

export type Theme = "light" | "dark";
export type ThemeChoice = Theme | "system";

export const THEME_CHOICES: ThemeChoice[] = ["dark", "light", "system"];

const STORAGE_KEY = "sok-theme";

/** The theme shown for a choice: the system one follows its dark mode. */
export function resolveTheme(choice: ThemeChoice, dark: boolean): Theme {
  if (choice !== "system") return choice;
  return dark ? "dark" : "light";
}

/** A saved choice; "orange", the bright theme of before 1.6, becomes light. */
export function savedChoice(saved: string | null): ThemeChoice {
  if (saved === "orange") return "light";
  return THEME_CHOICES.includes(saved as ThemeChoice) ? (saved as ThemeChoice) : "dark";
}

function readChoice(): ThemeChoice {
  try {
    return savedChoice(localStorage.getItem(STORAGE_KEY));
  } catch {
    // No storage (private window): the default.
    return "dark";
  }
}

// Read from the browser by startTheme().
const state = $state({ choice: "dark" as ThemeChoice, dark: true });

export const theme = {
  get choice() {
    return state.choice;
  },
  get current(): Theme {
    return resolveTheme(state.choice, state.dark);
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

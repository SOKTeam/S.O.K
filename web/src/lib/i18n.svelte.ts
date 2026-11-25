// The texts of the interface: the translation files of the desktop app,
// sent by GET /api/i18n.

import { api } from "./api";
import { fill, pluralForm } from "./format";

interface Texts {
  language: string;
  languages: string[];
  texts: Record<string, string>;
}

const state = $state<Texts>({ language: "en", languages: [], texts: {} });

export const i18n = {
  get language() {
    return state.language;
  },
  get languages() {
    return state.languages;
  },
};

/** Load the texts of a language; the one of the settings without one. */
export async function loadTexts(language?: string): Promise<void> {
  const query = language ? `?lang=${encodeURIComponent(language)}` : "";
  const answer = await api<Texts>(`/api/i18n${query}`);
  Object.assign(state, answer);
  document.documentElement.lang = answer.language;
}

/**
 * The text of a key in the language of the interface.
 *
 * @param key The key of the translation files.
 * @param english The English text, when the key is missing.
 * @param values The values of its {placeholders}.
 */
export function t(key: string, english: string, values?: Record<string, string | number>): string {
  return fill(state.texts[key] ?? english, values);
}

/**
 * The text of a number: the keys "<key>_one", "_few", "_many", "_other" (as
 * trn of the desktop app), a language without a form taking "_other", then
 * "_many". "{n}" is the number.
 *
 * @param one The English text for 1.
 * @param other The English text for any other number.
 */
export function tn(
  key: string,
  n: number,
  one: string,
  other: string,
  values?: Record<string, string | number>,
): string {
  const form = pluralForm(state.language, n);
  const texts = state.texts;
  const text =
    texts[`${key}_${form}`] ??
    texts[`${key}_other`] ??
    texts[`${key}_many`] ??
    (form === "one" ? one : other);
  return fill(text, { n, ...values });
}

// The text of an error of the API, in the language of the interface.

import { ApiError } from "./api";
import { t } from "./i18n.svelte";

export function errorText(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return t("web_error_unknown", "Something went wrong. Try again.");
  }
  switch (error.code) {
    case "offline":
      return t("web_error_offline", "The server does not answer.");
    case "invalid_account":
      return t(
        "web_error_invalid_account",
        "Give a user name, and a password of 8 characters or more.",
      );
    case "wrong_login":
      return t("web_error_wrong_login", "Wrong user name or password.");
    case "too_many_attempts":
      return t("web_error_too_many_attempts", "Too many attempts. Try again in {seconds} s.", {
        seconds: error.retryAfter ?? 30,
      });
    default:
      return t("web_error_unknown", "Something went wrong. Try again.");
  }
}

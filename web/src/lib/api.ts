// Calls to the API of the server, with the session cookie.

/** An answer of the API that is not a success. */
export class ApiError extends Error {
  /** The code of "detail" (wrong_login…), or "offline" without an answer. */
  readonly code: string;
  /** "detail" as the server gave it: a code, or an object with one. */
  readonly detail: unknown;
  /** Seconds to wait, from Retry-After (too_many_attempts). */
  readonly retryAfter: number | null;

  constructor(
    readonly status: number,
    detail: unknown,
    retryAfter: number | null = null,
  ) {
    const code =
      typeof detail === "string"
        ? detail
        : ((detail as { code?: string } | null)?.code ?? "unknown");
    super(code);
    this.code = code;
    this.detail = detail;
    this.retryAfter = retryAfter;
  }
}

/** GET (or another method with a JSON body) a route of /api. */
export async function api<T>(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: options.method ?? "GET",
      headers: options.body === undefined ? {} : { "Content-Type": "application/json" },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      credentials: "same-origin",
    });
  } catch {
    throw new ApiError(0, "offline");
  }
  if (response.status === 204) {
    return undefined as T;
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const retry = response.headers.get("Retry-After");
    throw new ApiError(response.status, data?.detail ?? null, retry ? Number(retry) : null);
  }
  return data as T;
}

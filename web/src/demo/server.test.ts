import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Operation } from "../lib/history";
import type { Rename } from "../lib/renames.svelte";
import type { Row } from "../lib/rows";
import type { Summary } from "../lib/scan.svelte";

type Server = typeof import("./server");

let server: Server;

/** Each test starts a new visit: a new state, as when the page is loaded. */
beforeEach(async () => {
  vi.useFakeTimers();
  vi.resetModules();
  server = await import("./server");
});

afterEach(() => {
  vi.useRealTimers();
});

/** Call a route, letting the time of the demo pass. */
async function call<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const answer = server.demoApi<T>(path, { method, body });
  await vi.advanceTimersByTimeAsync(1000);
  return answer;
}

/** Let the analysis or the rename that runs end. */
async function finish(): Promise<void> {
  await vi.advanceTimersByTimeAsync(10_000);
}

const rows = async (type: string) => (await call<{ rows: Row[] }>(`/api/rows?type=${type}`)).rows;
const summary = () => call<Summary>("/api/scans/current");

describe("demo server", () => {
  it("renames the Ready rows, then an undo and an analysis bring them back", async () => {
    const before = await rows("movies");
    const ready = before.filter((row) => row.status === "ok");
    expect(ready.length).toBeGreaterThan(0);

    await call("/api/renames", "POST", { type: "movies" });
    await finish();
    const { rename } = await call<{ rename: Rename }>("/api/renames/current");
    expect(rename.status).toBe("done");
    expect(rename.result?.renamed).toBe(ready.length);
    expect(rename.result?.subtitles).toBe(1);
    expect(await rows("movies")).toHaveLength(before.length - ready.length);

    const [operation] = (await call<{ operations: Operation[] }>("/api/history")).operations;
    expect(operation.media_type).toBe("movies");
    expect(operation.files[0].target).toMatch(/^\/media\/Movies\//);
    await call(`/api/history/${operation.id}/undo`, "POST", {});
    await call("/api/scans", "POST");
    await finish();
    expect(await rows("movies")).toHaveLength(before.length);
  });

  it("gives a row the names of the candidate picked", async () => {
    const office = (await rows("tv")).find((row) => row.title === "The Office")!;
    expect(office.status).toBe("ambiguous");
    const picked = await call<Row>(`/api/rows/${office.id}`, "PATCH", { selected: 1 });
    expect(picked.status).toBe("ok");
    expect(picked.selected).toBe(1);
    expect(picked.files[0].new_name).not.toBe(office.files[0].new_name);
  });

  it("finds the searches of the recording, and nothing else", async () => {
    const book = (await rows("books")).find((row) => row.status === "missing")!;
    const found = await call<Row>(`/api/rows/${book.id}/search`, "POST", {
      query: "le petit prince",
    });
    expect(found.candidates.length).toBeGreaterThan(0);
    const nothing = await call<Row>(`/api/rows/${book.id}/search`, "POST", { query: "xyz" });
    expect(nothing.status).toBe("missing");
    expect(nothing.candidates).toHaveLength(0);
  });

  it("keeps the type given to a file to check", async () => {
    const [item] = (await summary()).to_check;
    const games = (await rows("games")).length;
    await call("/api/to-check", "POST", { path: item.path, kind: item.kind });
    expect(await rows("games")).toHaveLength(games + 1);
    await call("/api/scans", "POST");
    await finish();
    expect((await summary()).to_check).toHaveLength(0);
    expect(await rows("games")).toHaveLength(games + 1);
  });

  it("sorts the file that arrives during the visit", async () => {
    await vi.advanceTimersByTimeAsync(40_000);
    await finish();
    const [operation] = (await call<{ operations: Operation[] }>("/api/history")).operations;
    expect(operation.auto).toBe(true);
    expect(operation.files[0].source).toMatch(/Oppenheimer/);
    const watch = await call<{ last_run: { renamed: number } }>("/api/watch");
    expect(watch.last_run.renamed).toBe(1);
  });

  it("refuses a folder that is not a path", async () => {
    const refused = expect(
      server.demoApi("/api/settings", {
        method: "PATCH",
        body: { folders: { movies: ["movies"] } },
      }),
    ).rejects.toMatchObject({ code: "invalid_folder" });
    await vi.advanceTimersByTimeAsync(1000);
    await refused;
  });
});

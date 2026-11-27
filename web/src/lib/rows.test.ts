import { describe, expect, it } from "vitest";

import {
  existingFolder,
  episodeCode,
  episodeTitle,
  platformOf,
  posterUrl,
  seasonsOf,
  statusOf,
  trackOf,
  type FolderMatch,
  type Row,
  type RowFile,
} from "./rows";

describe("posterUrl", () => {
  it("makes an address of a TMDB path", () => {
    expect(posterUrl("/abc.jpg")).toBe("https://image.tmdb.org/t/p/w154/abc.jpg");
  });

  it("keeps the address of another service", () => {
    expect(posterUrl("https://e-cdns-images.dzcdn.net/cover.jpg")).toBe(
      "https://e-cdns-images.dzcdn.net/cover.jpg",
    );
  });

  it("gives null without a poster", () => {
    expect(posterUrl(null)).toBeNull();
  });
});

function file(name: string, newName: string | null = null): RowFile {
  return { path: `/downloads/${name}`, name, new_name: newName, error: null };
}

describe("episodes", () => {
  it("reads the code of an episode from its new name, else its name", () => {
    expect(
      episodeCode(file("bb.mkv", "Breaking Bad/Season 1/Breaking Bad S01E04 Cancer Man.mkv")),
    ).toBe("S01E04");
    expect(episodeCode(file("Breaking Bad 1x04.avi"))).toBe("S01E04");
    expect(episodeCode(file("trailer.mkv"))).toBeNull();
  });

  it("reads the title of an episode from its new name", () => {
    expect(episodeTitle(file("x.mkv", "Dark/Season 1/Dark S01E01 Secrets.mkv"))).toBe("Secrets");
    expect(episodeTitle(file("x.mkv", "The Office/Season 2/The Office S02E01.mkv"))).toBeNull();
  });

  it("lists the seasons of a row", () => {
    const row = {
      files: [file("A.S02E01.mkv"), file("A.S01E03.mkv"), file("A.S02E02.mkv")],
    } as Row;
    expect(seasonsOf(row)).toEqual([1, 2]);
  });
});

describe("trackOf", () => {
  it("reads the number and the title of a track", () => {
    expect(trackOf(file("x.flac", "Daft Punk - Discovery/1 - One More Time.flac"))).toEqual({
      number: "01",
      title: "One More Time",
    });
  });

  it("keeps the name of a track without a number", () => {
    expect(trackOf(file("Queen - Bohemian Rhapsody.mp3"))).toEqual({
      number: null,
      title: "Queen - Bohemian Rhapsody",
    });
  });
});

describe("platformOf", () => {
  it("reads the console of a game from the folder of its new name", () => {
    const row = { files: [file("Chrono Trigger (USA).smc", "Super Nintendo/Chrono Trigger.smc")] };
    expect(platformOf(row as Row)).toBe("Super Nintendo");
    expect(platformOf({ files: [file("x.smc")] } as Row)).toBeNull();
  });
});

function series(extra: Partial<Row>): Row {
  return {
    id: 1,
    media_type: "tv",
    kind: "episode",
    title: "Severance",
    query: null,
    year: null,
    status: "ok",
    selected: 0,
    destination: 0,
    candidates: [],
    files: [],
    episodes_found: null,
    ...extra,
  };
}

const folder = (root: number): FolderMatch => ({
  path: `/tv${root}/Severance`,
  root,
  how: "title",
  source: null,
  title: "Severance",
  seasons: [1],
  episodes: 9,
});

describe("statusOf", () => {
  it("makes a series waiting for its folder a row to pick", () => {
    expect(statusOf(series({ folder_pending: true }))).toBe("ambiguous");
    expect(statusOf(series({ folder_pending: false }))).toBe("ok");
    expect(statusOf(series({ status: "missing" }))).toBe("missing");
  });
});

describe("existingFolder", () => {
  it("gives the folder chosen in the destination of the row", () => {
    const found = { matches: [folder(0), folder(1)], chosen: 1 as const };
    expect(existingFolder(series({ series_folder: found, destination: 1 }))?.root).toBe(1);
    // Another destination picked since: a new folder.
    expect(existingFolder(series({ series_folder: found, destination: 0 }))).toBeNull();
  });

  it("gives null for a new folder or before a choice", () => {
    expect(
      existingFolder(series({ series_folder: { matches: [folder(0)], chosen: "new" } })),
    ).toBeNull();
    expect(
      existingFolder(series({ series_folder: { matches: [folder(0)], chosen: null } })),
    ).toBeNull();
    expect(existingFolder(series({}))).toBeNull();
  });
});

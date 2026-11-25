import { describe, expect, it } from "vitest";

import { fillFormat, formatName, previewPath, type Piece } from "./namePreview";

const text = (pieces: Piece[] | null) => pieces?.map((piece) => piece.text).join("") ?? null;
const filled = (pieces: Piece[] | null) =>
  (pieces ?? []).filter((piece) => piece.filled).map((piece) => piece.text);

describe("fillFormat", () => {
  it("fills the fields of a model", () => {
    expect(fillFormat("{title} ({year})", { title: "Dune", year: "1965" })).toBe("Dune (1965)");
  });

  it("leaves out an empty value with what it leaves around it", () => {
    expect(fillFormat("{author} - {title} ({year})", { author: "A", title: "T" })).toBe("A - T");
    expect(fillFormat("{author} - {title}", { title: "T" })).toBe("T");
  });

  it("gives nothing for a model that is not valid", () => {
    expect(fillFormat("{title", { title: "T" })).toBe("");
    expect(fillFormat("{0}", { title: "T" })).toBe("");
    expect(fillFormat("{}", { title: "T" })).toBe("");
  });

  it("keeps doubled braces as braces", () => {
    expect(fillFormat("{{x}} {title}", { title: "T" })).toBe("{x} T");
  });
});

describe("formatName", () => {
  it("removes the forbidden characters and the dots at the end", () => {
    expect(formatName('Bag: "a"...')).toBe("Bag a");
    expect(formatName("Title... .mkv")).toBe("Title.mkv");
  });
});

describe("previewPath", () => {
  it("puts a movie at the root of its destination", () => {
    const path = previewPath("movies", "{title} ({year})", "/media/Films/", "Saison");
    expect(text(path)).toBe("/media/Films/Oppenheimer (2023).mkv");
    expect(filled(path)).toEqual(["Oppenheimer", "2023"]);
  });

  it("puts an episode in its series and season folders", () => {
    const path = previewPath("tv", "{title} S{season}E{episode}", "/tv", "Saison");
    expect(text(path)).toBe("/tv/Severance/Saison 2/Severance S02E01.mkv");
  });

  it("makes folders of the slashes of a music model", () => {
    const path = previewPath("music", "{artist}/{album}/{track} - {title}", "/m", "Season");
    expect(text(path)).toBe("/m/Daft Punk/Discovery/01 - One More Time.flac");
  });

  it("gives nothing when the model gives no name", () => {
    expect(previewPath("movies", "{nothing}", "/media", "Season")).toBeNull();
    expect(previewPath("movies", "{", "/media", "Season")).toBeNull();
  });
});

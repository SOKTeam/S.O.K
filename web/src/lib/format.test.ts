import { describe, expect, it } from "vitest";

import { daysAgo, dayKey, fill, parentFolder, pickLanguage, splitName } from "./format";

describe("fill", () => {
  it("puts the values in the placeholders", () => {
    expect(fill("Try again in {seconds} s.", { seconds: 30 })).toBe("Try again in 30 s.");
  });

  it("keeps a placeholder without a value", () => {
    expect(fill("{name} API Key required")).toBe("{name} API Key required");
  });
});

describe("pickLanguage", () => {
  const available = ["de", "en", "fr"];

  it("takes the first language S.O.K has", () => {
    expect(pickLanguage(["ja", "fr-CA", "en"], available)).toBe("fr");
  });

  it("gives null when none fits", () => {
    expect(pickLanguage(["ja"], available)).toBeNull();
  });
});

describe("parentFolder", () => {
  it("gives the folder that holds a path", () => {
    expect(parentFolder("/data/movies")).toBe("/data");
    expect(parentFolder("/data/movies/")).toBe("/data");
  });

  it("stops at the root", () => {
    expect(parentFolder("/data")).toBe("/");
  });
});

describe("splitName", () => {
  it("splits the folders from the file", () => {
    expect(splitName("Severance/Season 1/Severance S01E01.mkv")).toEqual({
      folder: "Severance/Season 1",
      name: "Severance S01E01.mkv",
    });
  });

  it("has no folder for a file alone", () => {
    expect(splitName("Dune (2021).mkv")).toEqual({ folder: "", name: "Dune (2021).mkv" });
  });
});

describe("days", () => {
  const today = new Date(2026, 9, 24, 9, 0);

  it("counts the days from midnight to midnight", () => {
    expect(daysAgo(new Date(2026, 9, 24, 23, 59), today)).toBe(0);
    expect(daysAgo(new Date(2026, 9, 23, 23, 59), today)).toBe(1);
    expect(daysAgo(new Date(2026, 8, 30), today)).toBe(24);
  });

  it("keys a date by its day", () => {
    expect(dayKey(new Date(2026, 0, 5, 18))).toBe("2026-01-05");
  });
});

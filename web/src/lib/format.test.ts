import { describe, expect, it } from "vitest";

import { fill, parentFolder, pickLanguage } from "./format";

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

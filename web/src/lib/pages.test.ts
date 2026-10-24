import { describe, expect, it } from "vitest";

import { pageOf } from "./pages";

describe("pageOf", () => {
  it("finds the page of a path", () => {
    expect(pageOf("/movies").mediaType).toBe("movies");
  });

  it("gives a sub-page to its page", () => {
    expect(pageOf("/history/processed").path).toBe("/history");
  });

  it("shows the analysis for an unknown path", () => {
    expect(pageOf("/nope").path).toBe("/");
  });
});

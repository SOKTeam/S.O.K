import { describe, expect, it } from "vitest";

import { resolveTheme, savedChoice } from "./theme.svelte";

describe("resolveTheme", () => {
  it("keeps a theme chosen by hand", () => {
    expect(resolveTheme("dark", false)).toBe("dark");
    expect(resolveTheme("light", true)).toBe("light");
  });

  it("follows the dark mode of the system", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
  });
});

describe("savedChoice", () => {
  it("is dark when nothing is saved", () => {
    expect(savedChoice(null)).toBe("dark");
    expect(savedChoice("purple")).toBe("dark");
  });

  it("keeps a known choice", () => {
    expect(savedChoice("system")).toBe("system");
    expect(savedChoice("light")).toBe("light");
  });

  it("turns the old orange theme into the light one", () => {
    expect(savedChoice("orange")).toBe("light");
  });
});

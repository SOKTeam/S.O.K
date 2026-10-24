import { describe, expect, it } from "vitest";

import { resolveTheme } from "./theme.svelte";

describe("resolveTheme", () => {
  it("keeps a theme chosen by hand", () => {
    expect(resolveTheme("orange", true, true)).toBe("orange");
    expect(resolveTheme("light", false, false)).toBe("light");
  });

  it("follows the dark mode of the system", () => {
    expect(resolveTheme("system", true, false)).toBe("dark");
  });

  it("is white on a Mac and orange elsewhere in light mode", () => {
    expect(resolveTheme("system", false, true)).toBe("light");
    expect(resolveTheme("system", false, false)).toBe("orange");
  });
});

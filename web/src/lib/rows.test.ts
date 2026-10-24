import { describe, expect, it } from "vitest";

import { posterUrl } from "./rows";

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

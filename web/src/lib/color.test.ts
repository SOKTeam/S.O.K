import { describe, expect, it } from "vitest";

import { averageOf } from "./color";

describe("averageOf", () => {
  it("averages the pixels", () => {
    expect(averageOf([200, 100, 0, 255, 100, 200, 0, 255])).toBe("150, 150, 0");
  });

  it("lifts a dark poster so it still lights", () => {
    expect(averageOf([30, 20, 10, 255])).toBe("120, 80, 40");
  });
});

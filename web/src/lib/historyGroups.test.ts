import { describe, expect, it } from "vitest";

import type { Operation } from "./history";
import { sectionsOf } from "./historyGroups";

const op = (date: string) => ({ id: date, date }) as Operation;
const today = new Date(2026, 10, 25, 12);

describe("sectionsOf", () => {
  it("puts today, yesterday, then earlier in the month", () => {
    const sections = sectionsOf(
      [
        op("2026-11-25T09:30"),
        op("2026-11-24T21:42"),
        op("2026-11-19T03:15"),
        op("2026-11-16T20:10"),
      ],
      today,
    );
    expect(sections.map((s) => [s.kind, s.operations.length, s.folded])).toEqual([
      ["today", 1, false],
      ["yesterday", 1, false],
      ["earlier", 2, false],
    ]);
  });

  it("folds the older months, one section each", () => {
    const sections = sectionsOf(
      [
        op("2026-11-20T10:00"),
        op("2026-10-30T10:00"),
        op("2026-10-02T10:00"),
        op("2026-09-01T10:00"),
      ],
      today,
    );
    expect(sections.map((s) => [s.kind, s.operations.length, s.folded])).toEqual([
      ["earlier", 1, false],
      ["month", 2, true],
      ["month", 1, true],
    ]);
  });

  it("sorts the operations, newest first", () => {
    const sections = sectionsOf([op("2026-11-19T03:15"), op("2026-11-25T09:30")], today);
    expect(sections.map((s) => s.kind)).toEqual(["today", "earlier"]);
  });

  it("shows the newest month even when it is not this one", () => {
    const sections = sectionsOf([op("2026-09-10T10:00")], today);
    expect(sections.map((s) => [s.kind, s.folded])).toEqual([["earlier", false]]);
  });
});

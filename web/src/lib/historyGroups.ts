// The sections of the History page, as in the desktop app: "Today",
// "Yesterday", "Earlier in <month>" for the month of the newest rename, then
// one folded section per older month.

import { daysAgo } from "./format";
import type { Operation } from "./history";

export interface Section {
  key: string;
  kind: "today" | "yesterday" | "earlier" | "month";
  /** A day of the section: yesterday's date, or a day of its month. */
  date: Date;
  operations: Operation[];
  /** An older month, shown as one line until it is opened. */
  folded: boolean;
}

function monthKey(date: Date): string {
  return `${date.getFullYear()}-${date.getMonth()}`;
}

/** The operations in their sections, newest first. */
export function sectionsOf(list: Operation[], today: Date): Section[] {
  const sections: Section[] = [];
  if (!list.length) return sections;
  const operations = [...list].sort((a, b) => Date.parse(b.date) - Date.parse(a.date));
  const newest = monthKey(new Date(operations[0].date));
  for (const operation of operations) {
    const date = new Date(operation.date);
    const ago = daysAgo(date, today);
    let kind: Section["kind"];
    let key: string;
    if (ago === 0) {
      kind = "today";
      key = "today";
    } else if (ago === 1) {
      kind = "yesterday";
      key = "yesterday";
    } else if (monthKey(date) === newest) {
      kind = "earlier";
      key = `earlier-${newest}`;
    } else {
      kind = "month";
      key = `month-${monthKey(date)}`;
    }
    let section = sections.find((one) => one.key === key);
    if (!section) {
      section = { key, kind, date, operations: [], folded: kind === "month" };
      sections.push(section);
    }
    section.operations.push(operation);
  }
  return sections;
}

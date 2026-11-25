// The disks of the folders, for "Your disks" on the Analysis screen.

import { api } from "./api";

export interface Disk {
  /** Its first folder, which names it. */
  path: string;
  folders: string[];
  total: number;
  free: number;
}

export interface Disks {
  disks: Disk[];
  /** The average size of the movies waiting, in bytes, or null. */
  movie_size: number | null;
}

export function loadDisks(): Promise<Disks> {
  return api<Disks>("/api/settings/disks");
}

/** A size in the units of the language: "2,9 To", "412 Go". */
export function sizeText(bytes: number, language: string): string {
  const units = language === "fr" ? ["o", "Ko", "Mo", "Go", "To"] : ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1000 && unit < units.length - 1) {
    value /= 1000;
    unit += 1;
  }
  const digits = value < 10 && unit > 0 ? 1 : 0;
  const number = new Intl.NumberFormat(language, { maximumFractionDigits: digits }).format(value);
  return `${number} ${units[unit]}`;
}

import { differenceInCalendarDays, parseISO } from "date-fns";
import type { PantryItemOut } from "~/lib/api/types/optimizer";

export function daysToExpiry(expirationDate: string | null | undefined): number | null {
  if (!expirationDate) return null;
  return differenceInCalendarDays(parseISO(expirationDate), new Date());
}

export type ExpirationSeverity = "expired" | "warning" | "ok" | "none";

export function expirationSeverity(days: number | null, warningThreshold = 3): ExpirationSeverity {
  if (days === null) return "none";
  if (days < 0) return "expired";
  if (days <= warningThreshold) return "warning";
  return "ok";
}

export function expirationColor(severity: ExpirationSeverity): string {
  switch (severity) {
    case "expired": return "error";
    case "warning": return "warning";
    case "ok": return "success";
    case "none": return "grey";
  }
}

export function expirationTextKey(
  days: number | null,
  prefix = "optimizer.pantry",
): { key: string; params?: Record<string, number> } | null {
  if (days === null) return null;
  if (days < 0) return { key: `${prefix}.expired` };
  if (days === 0) return { key: `${prefix}.expires-today` };
  return { key: `${prefix}.expires-in-days`, params: { days } };
}

export function sortByExpiration(items: PantryItemOut[]): PantryItemOut[] {
  return [...items].sort((a, b) => {
    const aDays = daysToExpiry(a.expirationDate);
    const bDays = daysToExpiry(b.expirationDate);

    // null expirationDate goes last
    if (aDays === null && bDays === null) return 0;
    if (aDays === null) return 1;
    if (bDays === null) return -1;

    // Sort ascending: most expired (most negative) first
    return aDays - bDays;
  });
}

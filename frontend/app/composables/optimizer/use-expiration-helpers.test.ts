import { describe, expect, it } from "vitest";
import {
  daysToExpiry,
  expirationColor,
  expirationSeverity,
  expirationTextKey,
  sortByExpiration,
} from "./use-expiration-helpers";
import type { PantryItemOut } from "~/lib/api/types/optimizer";

function makeFutureDate(daysFromNow: number): string {
  const d = new Date();
  d.setDate(d.getDate() + daysFromNow);
  return d.toISOString().split("T")[0];
}

describe("daysToExpiry", () => {
  it("returns null for null input", () => {
    expect(daysToExpiry(null)).toBeNull();
  });

  it("returns null for undefined input", () => {
    expect(daysToExpiry(undefined)).toBeNull();
  });

  it("returns 0 for today", () => {
    const today = new Date().toISOString().split("T")[0];
    expect(daysToExpiry(today)).toBe(0);
  });

  it("returns negative for past dates", () => {
    const result = daysToExpiry(makeFutureDate(-2));
    expect(result).toBe(-2);
  });

  it("returns positive for future dates", () => {
    const result = daysToExpiry(makeFutureDate(5));
    expect(result).toBe(5);
  });
});

describe("expirationSeverity", () => {
  it("returns 'none' for null days", () => {
    expect(expirationSeverity(null)).toBe("none");
  });

  it("returns 'expired' for negative days", () => {
    expect(expirationSeverity(-2)).toBe("expired");
  });

  it("returns 'warning' for days within threshold", () => {
    expect(expirationSeverity(0)).toBe("warning");
    expect(expirationSeverity(1)).toBe("warning");
    expect(expirationSeverity(3)).toBe("warning");
  });

  it("returns 'ok' for days above threshold", () => {
    expect(expirationSeverity(4)).toBe("ok");
    expect(expirationSeverity(10)).toBe("ok");
  });

  it("respects custom threshold", () => {
    expect(expirationSeverity(5, 7)).toBe("warning");
    expect(expirationSeverity(8, 7)).toBe("ok");
  });
});

describe("expirationColor", () => {
  it("returns 'error' for expired", () => {
    expect(expirationColor("expired")).toBe("error");
  });

  it("returns 'warning' for warning", () => {
    expect(expirationColor("warning")).toBe("warning");
  });

  it("returns 'success' for ok", () => {
    expect(expirationColor("ok")).toBe("success");
  });

  it("returns 'grey' for none", () => {
    expect(expirationColor("none")).toBe("grey");
  });
});

describe("expirationTextKey", () => {
  it("returns null for null days", () => {
    expect(expirationTextKey(null)).toBeNull();
  });

  it("returns expired key for negative days", () => {
    expect(expirationTextKey(-1)).toEqual({ key: "optimizer.pantry.expired" });
  });

  it("returns expires-today key for 0 days", () => {
    expect(expirationTextKey(0)).toEqual({ key: "optimizer.pantry.expires-today" });
  });

  it("returns expires-in-days with params for positive days", () => {
    expect(expirationTextKey(5)).toEqual({
      key: "optimizer.pantry.expires-in-days",
      params: { days: 5 },
    });
  });

  it("uses custom prefix", () => {
    expect(expirationTextKey(5, "optimizer.planner")).toEqual({
      key: "optimizer.planner.expires-in-days",
      params: { days: 5 },
    });
  });

  it("uses custom prefix for expired", () => {
    expect(expirationTextKey(-1, "optimizer.planner")).toEqual({
      key: "optimizer.planner.expired",
    });
  });
});

describe("sortByExpiration", () => {
  function makeItem(expirationDate: string | null, id = "test"): PantryItemOut {
    return {
      id,
      groupId: "g1",
      householdId: "h1",
      expirationDate,
    } as PantryItemOut;
  }

  it("returns empty array for empty input", () => {
    expect(sortByExpiration([])).toEqual([]);
  });

  it("sorts expired items first", () => {
    const items = [
      makeItem(makeFutureDate(5), "future"),
      makeItem(makeFutureDate(-2), "expired"),
      makeItem(makeFutureDate(1), "soon"),
    ];
    const sorted = sortByExpiration(items);
    expect(sorted[0].id).toBe("expired");
    expect(sorted[1].id).toBe("soon");
    expect(sorted[2].id).toBe("future");
  });

  it("puts null dates last", () => {
    const items = [
      makeItem(null, "nodate"),
      makeItem(makeFutureDate(2), "soon"),
      makeItem(makeFutureDate(-1), "expired"),
    ];
    const sorted = sortByExpiration(items);
    expect(sorted[0].id).toBe("expired");
    expect(sorted[1].id).toBe("soon");
    expect(sorted[2].id).toBe("nodate");
  });

  it("handles all-null dates", () => {
    const items = [
      makeItem(null, "a"),
      makeItem(null, "b"),
    ];
    const sorted = sortByExpiration(items);
    expect(sorted).toHaveLength(2);
  });

  it("does not mutate original array", () => {
    const items = [
      makeItem(makeFutureDate(5), "b"),
      makeItem(makeFutureDate(1), "a"),
    ];
    const sorted = sortByExpiration(items);
    expect(sorted).not.toBe(items);
    expect(items[0].id).toBe("b");
  });
});

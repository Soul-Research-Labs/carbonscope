/** Shared constants used across multiple pages. */

export const INDUSTRIES = [
  "energy",
  "manufacturing",
  "technology",
  "transportation",
  "retail",
  "healthcare",
  "finance",
  "construction",
  "agriculture",
  "other",
] as const;

export type Industry = (typeof INDUSTRIES)[number];

/** Title-case label for display (e.g. dropdowns). */
export function industryLabel(id: string): string {
  return id.charAt(0).toUpperCase() + id.slice(1);
}

export const REGIONS = [
  { value: "US", label: "United States" },
  { value: "EU", label: "European Union" },
  { value: "UK", label: "United Kingdom" },
  { value: "CN", label: "China" },
  { value: "IN", label: "India" },
  { value: "JP", label: "Japan" },
  { value: "AU", label: "Australia" },
  { value: "BR", label: "Brazil" },
  { value: "CA", label: "Canada" },
  { value: "OTHER", label: "Other" },
] as const;

export type Region = (typeof REGIONS)[number]["value"];

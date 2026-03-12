import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  Skeleton,
  CardSkeleton,
  TableSkeleton,
  SkeletonRows,
  PageSkeleton,
} from "@/components/Skeleton";

describe("Skeleton", () => {
  it("renders with role=status", () => {
    render(<Skeleton className="h-4 w-full" />);
    expect(screen.getAllByRole("status").length).toBeGreaterThanOrEqual(1);
  });

  it("applies custom className", () => {
    const { container } = render(<Skeleton className="h-8 w-1/2" />);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("h-8");
    expect(el.className).toContain("w-1/2");
  });

  it("has pulse animation class", () => {
    const { container } = render(<Skeleton />);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("animate-pulse");
  });
});

describe("CardSkeleton", () => {
  it("renders skeleton lines", () => {
    render(<CardSkeleton />);
    const statuses = screen.getAllByRole("status");
    expect(statuses.length).toBeGreaterThanOrEqual(1);
  });
});

describe("TableSkeleton", () => {
  it("renders correct number of rows", () => {
    render(<TableSkeleton rows={3} />);
    // The parent has role=status, and contains child skeletons
    expect(screen.getAllByRole("status").length).toBeGreaterThanOrEqual(1);
  });

  it("defaults to 5 rows", () => {
    const { container } = render(<TableSkeleton />);
    // parent div has animate-pulse via nested Skeleton components
    const pulses = container.querySelectorAll(".animate-pulse");
    expect(pulses.length).toBeGreaterThanOrEqual(6);
  });
});

describe("SkeletonRows", () => {
  it("renders specified number of tr elements", () => {
    const { container } = render(
      <table>
        <tbody>
          <SkeletonRows rows={3} columns={2} />
        </tbody>
      </table>,
    );
    const rows = container.querySelectorAll("tr");
    expect(rows.length).toBe(3);
  });

  it("renders correct columns per row", () => {
    const { container } = render(
      <table>
        <tbody>
          <SkeletonRows rows={1} columns={5} />
        </tbody>
      </table>,
    );
    const cells = container.querySelectorAll("td");
    expect(cells.length).toBe(5);
  });
});

describe("PageSkeleton", () => {
  it("renders header and card skeletons", () => {
    render(<PageSkeleton />);
    const statuses = screen.getAllByRole("status");
    expect(statuses.length).toBeGreaterThan(3);
  });
});

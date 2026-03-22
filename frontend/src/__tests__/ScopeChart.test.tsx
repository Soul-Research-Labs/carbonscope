import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

// Mock recharts to avoid canvas/SVG rendering issues in jsdom
vi.mock("recharts", async () => {
  const React = await import("react");
  return {
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) =>
      React.createElement(
        "div",
        { "data-testid": "responsive-container" },
        children,
      ),
    BarChart: ({
      children,
      data,
    }: {
      children: React.ReactNode;
      data: unknown[];
    }) =>
      React.createElement(
        "div",
        { "data-testid": "bar-chart", "data-len": data?.length },
        children,
      ),
    Bar: ({ children }: { children: React.ReactNode }) =>
      React.createElement("div", { "data-testid": "bar" }, children),
    XAxis: () => React.createElement("div", { "data-testid": "x-axis" }),
    YAxis: () => React.createElement("div", { "data-testid": "y-axis" }),
    Tooltip: () => React.createElement("div", { "data-testid": "tooltip" }),
    Cell: ({ fill }: { fill: string }) =>
      React.createElement("div", { "data-testid": "cell", "data-fill": fill }),
  };
});

import ScopeChart from "@/components/ScopeChart";

const SAMPLE_DATA = [
  { name: "Scope 1", value: 1200, fill: "#ef4444" },
  { name: "Scope 2", value: 3400, fill: "#3b82f6" },
  { name: "Scope 3", value: 5600, fill: "#22c55e" },
];

describe("ScopeChart", () => {
  it("renders a responsive container", () => {
    render(<ScopeChart data={SAMPLE_DATA} />);
    expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
  });

  it("renders a bar chart with the right data length", () => {
    render(<ScopeChart data={SAMPLE_DATA} />);
    const chart = screen.getByTestId("bar-chart");
    expect(chart).toHaveAttribute("data-len", "3");
  });

  it("renders a Cell per data point with correct fill", () => {
    render(<ScopeChart data={SAMPLE_DATA} />);
    const cells = screen.getAllByTestId("cell");
    expect(cells).toHaveLength(3);
    expect(cells[0]).toHaveAttribute("data-fill", "#ef4444");
    expect(cells[1]).toHaveAttribute("data-fill", "#3b82f6");
    expect(cells[2]).toHaveAttribute("data-fill", "#22c55e");
  });

  it("renders axes and tooltip", () => {
    render(<ScopeChart data={SAMPLE_DATA} />);
    expect(screen.getByTestId("x-axis")).toBeInTheDocument();
    expect(screen.getByTestId("y-axis")).toBeInTheDocument();
    expect(screen.getByTestId("tooltip")).toBeInTheDocument();
  });

  it("handles empty data gracefully", () => {
    render(<ScopeChart data={[]} />);
    expect(screen.getByTestId("bar-chart")).toHaveAttribute("data-len", "0");
  });
});

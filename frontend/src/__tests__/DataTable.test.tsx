import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DataTable, type Column } from "@/components/DataTable";

interface TestRow {
  id: string;
  name: string;
  value: number;
  [key: string]: unknown;
}

const columns: Column<TestRow>[] = [
  { key: "name", header: "Name" },
  { key: "value", header: "Value" },
];

const sampleData: TestRow[] = [
  { id: "1", name: "Alpha", value: 10 },
  { id: "2", name: "Beta", value: 20 },
  { id: "3", name: "Gamma", value: 30 },
];

describe("DataTable", () => {
  it("renders column headers", () => {
    render(<DataTable columns={columns} data={[]} />);
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Value")).toBeInTheDocument();
  });

  it("renders empty message when no data", () => {
    render(
      <DataTable columns={columns} data={[]} emptyMessage="Nothing here" />,
    );
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
  });

  it("renders default empty message", () => {
    render(<DataTable columns={columns} data={[]} />);
    expect(screen.getByText("No data found.")).toBeInTheDocument();
  });

  it("renders data rows", () => {
    render(<DataTable columns={columns} data={sampleData} />);
    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("20")).toBeInTheDocument();
    expect(screen.getByText("Gamma")).toBeInTheDocument();
  });

  it("shows loading state", () => {
    render(<DataTable columns={columns} data={[]} loading />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders custom column renderer", () => {
    const cols: Column<TestRow>[] = [
      { key: "name", header: "Name" },
      {
        key: "value",
        header: "Value",
        render: (row) => <strong>{row.value * 2}</strong>,
      },
    ];
    render(<DataTable columns={cols} data={sampleData} />);
    expect(screen.getByText("20")).toBeInTheDocument(); // 10 * 2
    expect(screen.getByText("60")).toBeInTheDocument(); // 30 * 2
  });

  it("renders pagination controls", () => {
    render(
      <DataTable
        columns={columns}
        data={sampleData.slice(0, 2)}
        total={3}
        limit={2}
        offset={0}
        onPageChange={() => {}}
      />,
    );
    expect(screen.getByText("Page 1 of 2 (3 items)")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next" })).toBeEnabled();
  });

  it("calls onPageChange when clicking Next", async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();
    render(
      <DataTable
        columns={columns}
        data={sampleData.slice(0, 2)}
        total={3}
        limit={2}
        offset={0}
        onPageChange={onPageChange}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it("disables Next on last page", () => {
    render(
      <DataTable
        columns={columns}
        data={sampleData.slice(2)}
        total={3}
        limit={2}
        offset={2}
        onPageChange={() => {}}
      />,
    );
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Previous" })).toBeEnabled();
  });

  it("does not render pagination when total fits in one page", () => {
    render(
      <DataTable
        columns={columns}
        data={sampleData}
        total={3}
        limit={10}
        offset={0}
        onPageChange={() => {}}
      />,
    );
    expect(screen.queryByText("Previous")).not.toBeInTheDocument();
  });
});

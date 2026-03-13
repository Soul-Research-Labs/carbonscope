import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

const mockReplace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockReplace }),
  usePathname: () => "/audit-logs",
  useSearchParams: () => new URLSearchParams(),
}));

const mockListAuditLogs = vi.fn();

vi.mock("@/lib/api", () => ({
  listAuditLogs: (...a: unknown[]) => mockListAuditLogs(...a),
  ApiError: class extends Error {
    status: number;
    constructor(msg: string, status: number) {
      super(msg);
      this.status = status;
    }
  },
}));

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({ user: { email: "u@test.com" }, loading: false }),
}));

vi.mock("@/components/Skeleton", () => ({
  SkeletonRows: () => (
    <tr>
      <td>Loading...</td>
    </tr>
  ),
}));

import AuditLogsPage from "@/app/audit-logs/page";

const LOGS = {
  items: [
    {
      id: "log1",
      action: "report.created",
      resource_type: "emission_report",
      resource_id: "r1",
      details: null,
      created_at: "2024-01-15T12:00:00Z",
    },
    {
      id: "log2",
      action: "data.uploaded",
      resource_type: "data_upload",
      resource_id: "u1",
      details: null,
      created_at: "2024-01-14T10:00:00Z",
    },
  ],
  total: 2,
};

describe("AuditLogsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListAuditLogs.mockResolvedValue(LOGS);
  });

  it("renders heading", async () => {
    render(<AuditLogsPage />);
    expect(await screen.findByText("Audit Log")).toBeInTheDocument();
  });

  it("renders table headers", async () => {
    render(<AuditLogsPage />);
    expect(await screen.findByText("Timestamp")).toBeInTheDocument();
    expect(screen.getByText("Action")).toBeInTheDocument();
    expect(screen.getByText("Resource")).toBeInTheDocument();
    expect(screen.getByText("Details")).toBeInTheDocument();
  });

  it("displays audit log entries", async () => {
    render(<AuditLogsPage />);
    expect(await screen.findByText("report.created")).toBeInTheDocument();
    expect(screen.getByText("data.uploaded")).toBeInTheDocument();
  });

  it("shows empty state when no logs", async () => {
    mockListAuditLogs.mockResolvedValue({ items: [], total: 0 });
    render(<AuditLogsPage />);
    expect(
      await screen.findByText(/No audit log entries found/),
    ).toBeInTheDocument();
  });

  it("shows error on API failure", async () => {
    mockListAuditLogs.mockRejectedValue(new Error("Failed to load audit logs"));
    render(<AuditLogsPage />);
    expect(
      await screen.findByText(/Failed to load audit logs/),
    ).toBeInTheDocument();
  });

  it("has table role for accessibility", async () => {
    render(<AuditLogsPage />);
    await screen.findByText("report.created");
    expect(screen.getByRole("table")).toBeInTheDocument();
  });
});

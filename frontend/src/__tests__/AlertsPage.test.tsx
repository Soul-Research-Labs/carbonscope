import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const mockReplace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockReplace }),
  usePathname: () => "/alerts",
  useSearchParams: () => new URLSearchParams(),
}));

const mockListAlerts = vi.fn();
const mockAcknowledgeAlert = vi.fn();
const mockTriggerAlertCheck = vi.fn();

vi.mock("@/lib/api", () => ({
  listAlerts: (...a: unknown[]) => mockListAlerts(...a),
  acknowledgeAlert: (...a: unknown[]) => mockAcknowledgeAlert(...a),
  triggerAlertCheck: (...a: unknown[]) => mockTriggerAlertCheck(...a),
}));

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({ user: { email: "u@test.com" }, loading: false }),
}));

vi.mock("@/components/Skeleton", () => ({
  PageSkeleton: () => <div>Loading...</div>,
}));

vi.mock("@/components/Toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

import AlertsPage from "@/app/alerts/page";

const ALERTS = {
  items: [
    {
      id: "a1",
      title: "Emissions spike",
      message: "Your Scope 1 increased 50%",
      severity: "critical",
      alert_type: "threshold",
      is_read: false,
      created_at: "2024-01-01T00:00:00Z",
    },
    {
      id: "a2",
      title: "New benchmark data",
      message: "Industry averages updated",
      severity: "info",
      alert_type: "update",
      is_read: true,
      created_at: "2024-01-02T00:00:00Z",
    },
  ],
  total: 2,
};

describe("AlertsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListAlerts.mockResolvedValue(ALERTS);
  });

  it("renders heading", async () => {
    render(<AlertsPage />);
    expect(await screen.findByText("Alerts")).toBeInTheDocument();
  });

  it("displays alert titles", async () => {
    render(<AlertsPage />);
    expect(await screen.findByText("Emissions spike")).toBeInTheDocument();
    expect(screen.getByText("New benchmark data")).toBeInTheDocument();
  });

  it("displays alert messages", async () => {
    render(<AlertsPage />);
    expect(
      await screen.findByText("Your Scope 1 increased 50%"),
    ).toBeInTheDocument();
  });

  it("has run check button", async () => {
    render(<AlertsPage />);
    expect(await screen.findByText("Run Check")).toBeInTheDocument();
  });

  it("triggers alert check", async () => {
    mockTriggerAlertCheck.mockResolvedValue({});
    render(<AlertsPage />);
    const btn = await screen.findByText("Run Check");
    fireEvent.click(btn);
    await waitFor(() => {
      expect(mockTriggerAlertCheck).toHaveBeenCalled();
    });
  });

  it("shows error on load failure", async () => {
    mockListAlerts.mockRejectedValue(new Error("Failed to load alerts"));
    render(<AlertsPage />);
    expect(
      await screen.findByText(/Failed to load alerts/),
    ).toBeInTheDocument();
  });

  it("has unread filter", async () => {
    render(<AlertsPage />);
    const checkbox = await screen.findByRole("checkbox");
    expect(checkbox).toBeInTheDocument();
  });
});

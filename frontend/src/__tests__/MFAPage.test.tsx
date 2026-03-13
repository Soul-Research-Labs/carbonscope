import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn() }),
  usePathname: () => "/mfa",
  useSearchParams: () => new URLSearchParams(),
}));

const mockGetMFAStatus = vi.fn();

vi.mock("@/lib/api", () => ({
  getMFAStatus: () => mockGetMFAStatus(),
  setupMFA: vi.fn(),
  verifyMFA: vi.fn(),
  disableMFA: vi.fn(),
}));

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({ user: { email: "test@example.com" }, loading: false }),
}));

import MFAPage from "@/app/mfa/page";

describe("MFAPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders heading", async () => {
    mockGetMFAStatus.mockResolvedValue({ mfa_enabled: false });
    render(<MFAPage />);
    expect(
      await screen.findByText("Multi-Factor Authentication"),
    ).toBeInTheDocument();
  });

  it("shows MFA disabled status", async () => {
    mockGetMFAStatus.mockResolvedValue({ mfa_enabled: false });
    render(<MFAPage />);
    expect(await screen.findByText("MFA is disabled")).toBeInTheDocument();
    expect(screen.getByText("Enable MFA")).toBeInTheDocument();
  });

  it("shows MFA enabled status with disable section", async () => {
    mockGetMFAStatus.mockResolvedValue({ mfa_enabled: true });
    render(<MFAPage />);
    expect(await screen.findByText("MFA is enabled")).toBeInTheDocument();
    expect(screen.getByText("Disable MFA")).toBeInTheDocument();
  });

  it("shows error on API failure", async () => {
    mockGetMFAStatus.mockRejectedValue(new Error("Connection failed"));
    render(<MFAPage />);
    expect(
      await screen.findByText(/Connection failed/),
    ).toBeInTheDocument();
  });
});

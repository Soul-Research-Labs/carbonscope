import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const mockReplace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockReplace }),
  usePathname: () => "/marketplace",
  useSearchParams: () => new URLSearchParams(),
}));

const mockBrowseListings = vi.fn();
const mockPurchaseListing = vi.fn();
const mockCreateListing = vi.fn();
const mockListReports = vi.fn();

vi.mock("@/lib/api", () => ({
  browseListings: (...a: unknown[]) => mockBrowseListings(...a),
  purchaseListing: (...a: unknown[]) => mockPurchaseListing(...a),
  createListing: (...a: unknown[]) => mockCreateListing(...a),
  listReports: (...a: unknown[]) => mockListReports(...a),
  ApiError: class ApiError extends Error {},
}));

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    user: { email: "u@test.com", company_id: "c1" },
    loading: false,
  }),
}));

vi.mock("@/components/Skeleton", () => ({
  PageSkeleton: () => <div>Loading...</div>,
}));

const mockToast = vi.fn();
vi.mock("@/components/Toast", () => ({
  useToast: () => ({ toast: mockToast }),
}));

type ConfirmDialogProps = {
  open: boolean;
  onConfirm: () => void;
  title: string;
};

vi.mock("@/components/ConfirmDialog", () => ({
  default: ({ open, onConfirm, title }: ConfirmDialogProps) =>
    open ? (
      <div data-testid="confirm-dialog">
        <span>{title}</span>
        <button onClick={onConfirm}>Confirm</button>
      </div>
    ) : null,
}));

import MarketplacePage from "@/app/marketplace/page";

const LISTING = {
  id: "lst1",
  title: "2024 Emissions Data",
  description: "Anonymized data",
  data_type: "emission_report",
  seller_id: "other",
  industry: "tech",
  region: "US",
  price_credits: 10,
  status: "active",
  created_at: "2024-01-01T00:00:00Z",
};

describe("MarketplacePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockBrowseListings.mockResolvedValue({
      items: [LISTING],
      total: 1,
    });
    mockListReports.mockResolvedValue({ items: [], total: 0 });
  });

  it("renders heading and listings", async () => {
    render(<MarketplacePage />);
    expect(await screen.findByText("Data Marketplace")).toBeInTheDocument();
    expect(await screen.findByText("2024 Emissions Data")).toBeInTheDocument();
  });

  it("shows listing count", async () => {
    render(<MarketplacePage />);
    expect(await screen.findByText(/1 listing\b/)).toBeInTheDocument();
  });

  it("applies industry/region filter", async () => {
    render(<MarketplacePage />);
    await screen.findByText("Data Marketplace");

    const industryInput = screen.getByPlaceholderText(/filter by industry/i);
    fireEvent.change(industryInput, { target: { value: "energy" } });

    fireEvent.click(screen.getByText("Apply"));

    await waitFor(() => {
      expect(mockBrowseListings).toHaveBeenCalledWith(
        expect.objectContaining({ industry: "energy" }),
      );
    });
  });

  it("opens create listing modal", async () => {
    render(<MarketplacePage />);
    fireEvent.click(await screen.findByText("+ Create Listing"));
    expect(await screen.findByText("Create New Listing")).toBeInTheDocument();
  });

  it("shows error on fetch failure", async () => {
    mockBrowseListings.mockRejectedValue(new Error("network error"));
    render(<MarketplacePage />);
    expect(await screen.findByText(/Error:/)).toBeInTheDocument();
  });
});

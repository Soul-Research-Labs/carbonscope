import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const mockRegister = vi.fn();
vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({ register: mockRegister }),
}));

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
}));

vi.mock("@/components/FormField", () => ({
  FormField: ({
    label,
    type,
    value,
    onChange,
    error,
    children,
  }: {
    label: string;
    type?: string;
    value?: string;
    onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
    error?: string;
    children?: React.ReactNode;
  }) => (
    <div>
      <label htmlFor={label}>{label}</label>
      {children ? (
        children
      ) : (
        <input
          id={label}
          type={type}
          value={value}
          onChange={onChange}
          aria-label={label}
        />
      )}
      {error && <span>{error}</span>}
    </div>
  ),
}));

vi.mock("@/lib/validation", () => ({
  validateRegisterField: vi.fn().mockReturnValue(null),
  validateRegisterForm: vi.fn().mockReturnValue({}),
}));

import RegisterPage from "@/app/register/page";

describe("RegisterPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the registration form", () => {
    render(<RegisterPage />);
    expect(screen.getByText(/create your account/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /create account/i }),
    ).toBeInTheDocument();
  });

  it("renders link to sign in", () => {
    render(<RegisterPage />);
    const link = screen.getByRole("link", { name: /sign in/i });
    expect(link).toHaveAttribute("href", "/login");
  });

  it("calls register on valid form submit", async () => {
    mockRegister.mockResolvedValueOnce(undefined);
    render(<RegisterPage />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "new@test.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "StrongPass1!" },
    });
    fireEvent.change(screen.getByLabelText(/confirm password/i), {
      target: { value: "StrongPass1!" },
    });
    fireEvent.change(screen.getByLabelText(/full name/i), {
      target: { value: "Test User" },
    });
    fireEvent.change(screen.getByLabelText(/company name/i), {
      target: { value: "ACME Corp" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalled();
    });
  });

  it("shows 409 conflict error for duplicate email", async () => {
    const err = Object.assign(new Error("Email already in use"), {
      status: 409,
    });
    mockRegister.mockRejectedValueOnce(err);
    render(<RegisterPage />);

    fireEvent.click(screen.getByRole("button", { name: /create account/i }));
    expect(
      await screen.findByText(/account with this email already exists/i),
    ).toBeInTheDocument();
  });

  it("shows 429 rate-limit error", async () => {
    const err = Object.assign(new Error("Too many requests"), { status: 429 });
    mockRegister.mockRejectedValueOnce(err);
    render(<RegisterPage />);

    fireEvent.click(screen.getByRole("button", { name: /create account/i }));
    expect(await screen.findByText(/too many requests/i)).toBeInTheDocument();
  });

  it("shows generic error on unexpected failure", async () => {
    mockRegister.mockRejectedValueOnce(new Error("Network error"));
    render(<RegisterPage />);

    fireEvent.click(screen.getByRole("button", { name: /create account/i }));
    expect(await screen.findByText("Network error")).toBeInTheDocument();
  });
});

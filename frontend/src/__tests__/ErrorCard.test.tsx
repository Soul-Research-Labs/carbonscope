import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ErrorCard } from "@/components/ErrorCard";

describe("ErrorCard", () => {
  it("renders default title and message", () => {
    render(<ErrorCard message="Network error" />);
    expect(screen.getByText("Something went wrong")).toBeTruthy();
    expect(screen.getByText("Network error")).toBeTruthy();
  });

  it("renders custom title", () => {
    render(<ErrorCard message="Oops" title="Custom Title" />);
    expect(screen.getByText("Custom Title")).toBeTruthy();
  });

  it("has alert role", () => {
    render(<ErrorCard message="fail" />);
    expect(screen.getByRole("alert")).toBeTruthy();
  });

  it("shows Try Again button when onRetry is provided", () => {
    const fn = vi.fn();
    render(<ErrorCard message="fail" onRetry={fn} />);
    const btn = screen.getByText("Try Again");
    expect(btn).toBeTruthy();
    fireEvent.click(btn);
    expect(fn).toHaveBeenCalledOnce();
  });

  it("hides Try Again button when onRetry is not provided", () => {
    render(<ErrorCard message="fail" />);
    expect(screen.queryByText("Try Again")).toBeNull();
  });
});

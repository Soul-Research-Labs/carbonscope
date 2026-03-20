import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { ToastProvider, useToast } from "@/components/Toast";

function TestConsumer() {
  const { toast } = useToast();
  return (
    <div>
      <button onClick={() => toast("Success!", "success")}>Show success</button>
      <button onClick={() => toast("Error!", "error")}>Show error</button>
      <button onClick={() => toast("Info message")}>Show info</button>
    </div>
  );
}

describe("Toast", () => {
  it("renders children within provider", () => {
    render(
      <ToastProvider>
        <div>child content</div>
      </ToastProvider>,
    );
    expect(screen.getByText("child content")).toBeInTheDocument();
  });

  it("shows a toast on trigger", () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>,
    );
    fireEvent.click(screen.getByText("Show success"));
    expect(screen.getByText("Success!")).toBeInTheDocument();
  });

  it("shows multiple toasts", () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>,
    );
    fireEvent.click(screen.getByText("Show success"));
    fireEvent.click(screen.getByText("Show error"));
    expect(screen.getByText("Success!")).toBeInTheDocument();
    expect(screen.getByText("Error!")).toBeInTheDocument();
  });

  it("defaults to info type", () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>,
    );
    fireEvent.click(screen.getByText("Show info"));
    expect(screen.getByText("Info message")).toBeInTheDocument();
  });

  it("dismisses toast on dismiss button click", () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>,
    );
    fireEvent.click(screen.getByText("Show success"));
    expect(screen.getByText("Success!")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Dismiss notification"));
    expect(screen.queryByText("Success!")).not.toBeInTheDocument();
  });

  it("auto-dismisses after timeout", () => {
    vi.useFakeTimers();
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>,
    );
    fireEvent.click(screen.getByText("Show success"));
    expect(screen.getByText("Success!")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(4500);
    });
    expect(screen.queryByText("Success!")).not.toBeInTheDocument();
    vi.useRealTimers();
  });

  it("has proper ARIA live region", () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>,
    );
    // Trigger an info toast so the status element appears
    fireEvent.click(screen.getByText("Show info"));
    const region = screen.getByRole("status");
    expect(region).toHaveAttribute("aria-live", "polite");
  });

  it("uses assertive aria-live for error toasts", () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>,
    );
    fireEvent.click(screen.getByText("Show error"));
    const region = screen.getByRole("alert");
    expect(region).toHaveAttribute("aria-live", "assertive");
  });

  it("throws when used outside provider", () => {
    expect(() => {
      render(<TestConsumer />);
    }).toThrow("useToast must be used within <ToastProvider>");
  });
});

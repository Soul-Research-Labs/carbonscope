import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusMessage } from "@/components/StatusMessage";

describe("StatusMessage", () => {
  it("renders nothing when message is empty", () => {
    const { container } = render(<StatusMessage message="" variant="error" />);
    expect(container.firstChild).toBeNull();
  });

  it("renders error message with alert role", () => {
    render(<StatusMessage message="Something went wrong" variant="error" />);
    const el = screen.getByRole("alert");
    expect(el).toHaveTextContent("Something went wrong");
  });

  it("renders success message with status role", () => {
    render(<StatusMessage message="Saved!" variant="success" />);
    const el = screen.getByRole("status");
    expect(el).toHaveTextContent("Saved!");
  });

  it("applies error color style", () => {
    render(<StatusMessage message="err" variant="error" />);
    const el = screen.getByRole("alert");
    expect(el.style.color).toBe("var(--danger)");
  });

  it("applies success color style", () => {
    render(<StatusMessage message="ok" variant="success" />);
    const el = screen.getByRole("status");
    expect(el.style.color).toBe("var(--primary)");
  });
});

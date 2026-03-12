import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FormField } from "@/components/FormField";

describe("FormField", () => {
  it("renders label and input", () => {
    render(<FormField label="Email" type="email" placeholder="you@example.com" />);
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("you@example.com")).toBeInTheDocument();
  });

  it("shows error message", () => {
    render(<FormField label="Password" error="Too short" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Too short");
    expect(screen.getByLabelText("Password")).toHaveAttribute("aria-invalid", "true");
  });

  it("shows hint when no error", () => {
    render(<FormField label="Name" hint="Enter your full name" />);
    expect(screen.getByText("Enter your full name")).toBeInTheDocument();
  });

  it("prefers error over hint", () => {
    render(<FormField label="Name" error="Required" hint="Enter your name" />);
    expect(screen.getByText("Required")).toBeInTheDocument();
    expect(screen.queryByText("Enter your name")).not.toBeInTheDocument();
  });

  it("renders children instead of default input", () => {
    render(
      <FormField label="Custom">
        <select data-testid="custom-select">
          <option>A</option>
        </select>
      </FormField>,
    );
    expect(screen.getByTestId("custom-select")).toBeInTheDocument();
    // No default input element
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("passes input props through", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<FormField label="Test" onChange={onChange} />);
    await user.type(screen.getByLabelText("Test"), "hello");
    expect(onChange).toHaveBeenCalled();
  });

  it("applies error styling", () => {
    const { container } = render(<FormField label="Field" error="Bad" />);
    const input = container.querySelector("input");
    expect(input?.className).toContain("border-red-500");
  });

  it("applies normal styling without error", () => {
    const { container } = render(<FormField label="Field" />);
    const input = container.querySelector("input");
    expect(input?.className).toContain("border-gray-300");
  });
});

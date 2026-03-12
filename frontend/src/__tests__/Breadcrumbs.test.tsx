import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import Breadcrumbs from "@/components/Breadcrumbs";

describe("Breadcrumbs", () => {
  it("renders nothing for empty items", () => {
    const { container } = render(<Breadcrumbs items={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders single item as current page", () => {
    render(<Breadcrumbs items={[{ label: "Dashboard" }]} />);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("renders links for non-last items", () => {
    render(
      <Breadcrumbs
        items={[
          { label: "Home", href: "/" },
          { label: "Reports", href: "/reports" },
          { label: "Detail" },
        ]}
      />,
    );
    const homeLink = screen.getByRole("link", { name: "Home" });
    expect(homeLink).toHaveAttribute("href", "/");
    const reportsLink = screen.getByRole("link", { name: "Reports" });
    expect(reportsLink).toHaveAttribute("href", "/reports");
    // Last item should not be a link
    const detail = screen.getByText("Detail");
    expect(detail.tagName).not.toBe("A");
  });

  it("has accessible nav landmark", () => {
    render(
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Page" }]} />,
    );
    expect(screen.getByRole("navigation", { name: "Breadcrumb" })).toBeInTheDocument();
  });

  it("renders separator between items", () => {
    render(
      <Breadcrumbs items={[{ label: "A", href: "/" }, { label: "B" }]} />,
    );
    expect(screen.getByText("/")).toBeInTheDocument();
  });
});

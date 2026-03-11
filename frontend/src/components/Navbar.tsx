"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: "📊" },
  { href: "/upload", label: "Upload Data", icon: "📤" },
  { href: "/reports", label: "Reports", icon: "📋" },
  { href: "/questionnaires", label: "Questionnaires", icon: "📝" },
  { href: "/scenarios", label: "Scenarios", icon: "🔮" },
  { href: "/supply-chain", label: "Supply Chain", icon: "🔗" },
  { href: "/compliance", label: "Compliance", icon: "📑" },
  { href: "/marketplace", label: "Marketplace", icon: "🏪" },
  { href: "/alerts", label: "Alerts", icon: "🔔" },
  { href: "/audit-logs", label: "Audit Log", icon: "📜" },
  { href: "/billing", label: "Billing", icon: "💳" },
  { href: "/settings", label: "Settings", icon: "⚙️" },
];

export default function Navbar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  // Close mobile menu on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  if (!user) return null;

  return (
    <nav
      className="border-b border-[var(--card-border)] bg-[var(--card)]"
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="flex items-center justify-between px-6 py-3">
        <div className="flex items-center gap-8">
          <Link
            href="/dashboard"
            className="text-lg font-bold text-[var(--primary)]"
          >
            🌿 CarbonScope
          </Link>
          {/* Desktop nav */}
          <div className="hidden lg:flex gap-1">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  pathname === item.href
                    ? "bg-[var(--primary)] text-black"
                    : "text-[var(--muted)] hover:text-[var(--foreground)]"
                }`}
              >
                {item.icon} {item.label}
              </Link>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className="hidden sm:inline text-sm text-[var(--muted)]">
            {user.email}
          </span>
          <button
            onClick={logout}
            className="text-sm text-[var(--muted)] hover:text-[var(--danger)] transition-colors"
          >
            Logout
          </button>
          {/* Mobile hamburger */}
          <button
            className="lg:hidden p-1 text-[var(--muted)] hover:text-[var(--foreground)]"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-expanded={mobileOpen}
            aria-controls="mobile-nav"
            aria-label="Toggle navigation menu"
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            >
              {mobileOpen ? (
                <>
                  <line x1="6" y1="6" x2="18" y2="18" />
                  <line x1="6" y1="18" x2="18" y2="6" />
                </>
              ) : (
                <>
                  <line x1="3" y1="6" x2="21" y2="6" />
                  <line x1="3" y1="12" x2="21" y2="12" />
                  <line x1="3" y1="18" x2="21" y2="18" />
                </>
              )}
            </svg>
          </button>
        </div>
      </div>
      {/* Mobile nav panel */}
      {mobileOpen && (
        <div
          id="mobile-nav"
          className="lg:hidden border-t border-[var(--card-border)] px-4 py-2 grid grid-cols-2 gap-1"
        >
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                pathname === item.href
                  ? "bg-[var(--primary)] text-black"
                  : "text-[var(--muted)] hover:text-[var(--foreground)]"
              }`}
            >
              {item.icon} {item.label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  );
}

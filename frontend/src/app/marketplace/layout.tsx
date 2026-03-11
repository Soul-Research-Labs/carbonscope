import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Marketplace",
  description: "Browse and purchase carbon emission datasets",
};

export default function MarketplaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}

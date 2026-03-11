import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Supply Chain",
  description: "Scope 3 supply chain emission tracking and analysis",
};

export default function SupplyChainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}

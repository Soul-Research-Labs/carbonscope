import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Compliance",
  description: "GHG Protocol compliance reporting and verification",
};

export default function ComplianceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}

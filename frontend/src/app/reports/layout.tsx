import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Reports",
  description: "View and manage your carbon emission reports",
};

export default function ReportsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}

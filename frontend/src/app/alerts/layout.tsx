import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Alerts",
  description: "Emission threshold alerts and notifications",
};

export default function AlertsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}

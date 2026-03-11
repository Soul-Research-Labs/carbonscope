import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Billing",
  description: "Manage your subscription plan and credit balance",
};

export default function BillingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}

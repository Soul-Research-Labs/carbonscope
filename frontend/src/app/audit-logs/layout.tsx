import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Audit Log",
  description: "View activity and audit trail for your organization",
};

export default function AuditLogsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}

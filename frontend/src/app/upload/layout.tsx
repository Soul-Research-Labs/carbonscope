import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Upload Data",
  description: "Upload emissions data files for analysis and reporting",
};

export default function UploadLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}

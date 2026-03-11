import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "What-If Scenarios",
  description: "Model and compare emission reduction scenarios",
};

export default function ScenariosLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}

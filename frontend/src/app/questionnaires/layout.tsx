import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Questionnaires",
  description: "Carbon emission questionnaires and data collection forms",
};

export default function QuestionnairesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}

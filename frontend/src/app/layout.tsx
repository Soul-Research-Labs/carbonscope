import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { ToastProvider } from "@/components/Toast";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: {
    default: "CarbonScope",
    template: "%s | CarbonScope",
  },
  description:
    "Decentralized corporate carbon emission intelligence powered by Bittensor",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <ToastProvider>
            <a
              href="#main-content"
              className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:bg-[var(--primary)] focus:text-black focus:px-4 focus:py-2 focus:rounded-lg"
            >
              Skip to main content
            </a>
            <Navbar />
            <main
              id="main-content"
              className="min-h-[calc(100vh-49px)]"
              role="main"
            >
              {children}
            </main>
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  );
}

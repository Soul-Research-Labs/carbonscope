import React from "react";
import { ToastProvider } from "@/components/Toast";

/** Wraps children in all providers needed for component tests. */
export function TestProviders({ children }: { children: React.ReactNode }) {
  return <ToastProvider>{children}</ToastProvider>;
}

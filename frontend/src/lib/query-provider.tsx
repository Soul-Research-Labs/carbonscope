"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { getQueryClient } from "@/lib/query-client";
import { useWebVitals } from "@/hooks/useWebVitals";

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const queryClient = getQueryClient();
  useWebVitals();
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

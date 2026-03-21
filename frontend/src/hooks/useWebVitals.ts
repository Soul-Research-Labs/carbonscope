"use client";

import { useEffect } from "react";

type WebVitalMetric = {
  name: string;
  value: number;
  id: string;
};

/**
 * Report Web Vitals (CLS, LCP, FID/INP) to the console in development
 * and to an analytics endpoint in production.
 */
export function useWebVitals() {
  useEffect(() => {
    if (typeof window === "undefined") return;

    import("web-vitals")
      .then(({ onCLS, onLCP, onINP, onFCP, onTTFB }) => {
        const report = (metric: WebVitalMetric) => {
          if (process.env.NODE_ENV === "development") {
            console.debug(
              `[Web Vital] ${metric.name}: ${metric.value.toFixed(2)}`,
            );
          }
          // In production, send to /api/v1/telemetry or your analytics endpoint
          if (
            process.env.NODE_ENV === "production" &&
            process.env.NEXT_PUBLIC_VITALS_ENDPOINT
          ) {
            const body = JSON.stringify({
              name: metric.name,
              value: metric.value,
              id: metric.id,
            });
            // Use sendBeacon for reliability on page unload
            if (navigator.sendBeacon) {
              navigator.sendBeacon(
                process.env.NEXT_PUBLIC_VITALS_ENDPOINT,
                body,
              );
            }
          }
        };

        onCLS(report);
        onLCP(report);
        onINP(report);
        onFCP(report);
        onTTFB(report);
      })
      .catch(() => {
        // web-vitals not installed — silently skip
      });
  }, []);
}

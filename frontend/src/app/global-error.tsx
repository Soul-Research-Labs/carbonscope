"use client";

/**
 * Global error boundary — catches errors in the root layout itself
 * (Navbar, providers, etc.) that error.tsx cannot handle.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100vh",
          fontFamily: "system-ui, sans-serif",
          background: "#0a0a0a",
          color: "#e5e5e5",
          margin: 0,
        }}
      >
        <div
          style={{
            maxWidth: 420,
            textAlign: "center",
            padding: 32,
            border: "1px solid #333",
            borderRadius: 12,
          }}
        >
          <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
            Something went wrong
          </h2>
          <p style={{ color: "#999", fontSize: 14, marginBottom: 24 }}>
            {error.digest
              ? `Error reference: ${error.digest}`
              : "An unexpected error occurred. Please try again."}
          </p>
          <button
            onClick={reset}
            style={{
              background: "#00C853",
              color: "#000",
              border: "none",
              padding: "10px 24px",
              borderRadius: 8,
              fontWeight: 600,
              cursor: "pointer",
              fontSize: 14,
            }}
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}

/**
 * Runtime environment validation.
 *
 * Imported once in layout.tsx (server side) so misconfigurations are
 * caught at build / startup rather than at request time.
 */

function required(key: string): string {
  const value = process.env[key];
  if (!value) {
    throw new Error(
      `Missing required environment variable: ${key}. ` +
        "Check .env.local or your deployment config.",
    );
  }
  return value;
}

function optional(key: string, fallback: string): string {
  return process.env[key] || fallback;
}

/** Validated server-side environment variables. */
export const env = {
  BACKEND_URL: optional("BACKEND_URL", "http://localhost:8000"),
  NODE_ENV: optional("NODE_ENV", "development"),
  NEXT_PUBLIC_SITE_URL: optional(
    "NEXT_PUBLIC_SITE_URL",
    "https://carbonscope.io",
  ),
} as const;

/**
 * Call once at startup to make sure all required vars are present.
 * In production, missing vars cause a hard failure.
 */
export function validateEnv(): void {
  if (env.NODE_ENV === "production") {
    required("BACKEND_URL");
  }
}

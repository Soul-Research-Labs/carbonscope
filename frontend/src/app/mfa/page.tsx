"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { PageSkeleton } from "@/components/Skeleton";
import { StatusMessage } from "@/components/StatusMessage";
import Breadcrumbs from "@/components/Breadcrumbs";
import {
  getMFAStatus,
  setupMFA,
  verifyMFA,
  disableMFA,
  type MFAStatus,
  type MFASetup,
} from "@/lib/api";

export default function MFAPage() {
  useDocumentTitle("Multi-Factor Authentication");
  const { user, loading } = useRequireAuth();
  const [setup, setSetup] = useState<MFASetup | null>(null);
  const [totpCode, setTotpCode] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const statusQuery = useQuery<MFAStatus>({
    queryKey: ["mfa-status"],
    queryFn: () => getMFAStatus(),
    enabled: !!user && !loading,
  });

  const status = statusQuery.data ?? null;

  const handleSetup = async () => {
    setError("");
    setSuccess("");
    try {
      const s = await setupMFA();
      setSetup(s);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "MFA setup failed");
    }
  };

  const handleVerify = async () => {
    setError("");
    try {
      await verifyMFA(totpCode);
      setSuccess("MFA enabled successfully!");
      setSetup(null);
      setTotpCode("");
      statusQuery.refetch();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Invalid TOTP code");
    }
  };

  const handleDisable = async () => {
    setError("");
    try {
      await disableMFA(disableCode);
      setSuccess("MFA disabled.");
      setDisableCode("");
      statusQuery.refetch();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to disable MFA");
    }
  };

  if (loading) return <PageSkeleton />;
  if (!user) return null;

  return (
    <div className="mx-auto max-w-2xl p-8">
      <Breadcrumbs
        items={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Settings", href: "/settings" },
          { label: "MFA" },
        ]}
      />
      <h1 className="mb-8 text-2xl font-bold">Multi-Factor Authentication</h1>

      {error && (
        <div className="mb-4">
          <StatusMessage message={error} variant="error" />
        </div>
      )}
      {success && (
        <div className="mb-4">
          <StatusMessage message={success} variant="success" />
        </div>
      )}

      {status && (
        <div className="mb-6 rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-6">
          <div className="flex items-center gap-3">
            <div
              className={`h-3 w-3 rounded-full ${
                status.mfa_enabled ? "bg-[var(--primary)]" : "bg-[var(--muted)]"
              }`}
            />
            <p className="text-lg font-medium">
              MFA is {status.mfa_enabled ? "enabled" : "disabled"}
            </p>
          </div>
        </div>
      )}

      {/* Setup flow */}
      {status && !status.mfa_enabled && !setup && (
        <button onClick={handleSetup} className="btn-primary px-6 py-3">
          Enable MFA
        </button>
      )}

      {setup && (
        <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-6">
          <h2 className="mb-4 text-xl font-semibold">Setup TOTP</h2>

          <div className="mb-4">
            <p className="mb-1 text-sm text-[var(--muted)]">
              Scan this QR code with your authenticator app, or enter the secret
              manually:
            </p>
            <code className="block rounded bg-[var(--background)] p-3 text-sm text-[var(--primary)] break-all">
              {setup.secret}
            </code>
          </div>

          <div className="mb-4">
            <p className="mb-1 text-sm text-[var(--muted)]">
              Backup codes (save securely):
            </p>
            <div className="grid grid-cols-2 gap-1">
              {setup.backup_codes.map((code, i) => (
                <code
                  key={i}
                  className="rounded bg-[var(--background)] px-2 py-1 text-sm"
                >
                  {code}
                </code>
              ))}
            </div>
          </div>

          <div className="flex gap-3">
            <input
              className="input"
              placeholder="Enter TOTP code"
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value)}
              maxLength={6}
              inputMode="numeric"
              pattern="[0-9]*"
              aria-label="TOTP verification code"
            />
            <button onClick={handleVerify} className="btn-primary">
              Verify & Enable
            </button>
          </div>
        </div>
      )}

      {/* Disable MFA */}
      {status?.mfa_enabled && (
        <div
          className="mt-6 rounded-lg border p-6"
          style={{
            borderColor: "var(--danger)",
            background: "color-mix(in srgb, var(--danger) 10%, transparent)",
          }}
        >
          <h2
            className="mb-2 text-lg font-semibold"
            style={{ color: "var(--danger)" }}
          >
            Disable MFA
          </h2>
          <p className="mb-4 text-sm text-[var(--muted)]">
            Enter your current TOTP code to disable multi-factor authentication.
          </p>
          <div className="flex gap-3">
            <input
              className="input"
              placeholder="TOTP code"
              value={disableCode}
              onChange={(e) => setDisableCode(e.target.value)}
              maxLength={6}
              inputMode="numeric"
              pattern="[0-9]*"
              aria-label="TOTP code to disable MFA"
            />
            <button onClick={handleDisable} className="btn-danger">
              Disable
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

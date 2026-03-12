import { describe, it, expect, vi, beforeEach } from "vitest";

describe("Auto token refresh", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.restoreAllMocks();
  });

  it("retries request after refreshing token on 401", async () => {
    let callCount = 0;
    const mockFetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/auth/refresh")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ access_token: "new-token" }),
        });
      }
      callCount++;
      if (callCount === 1) {
        // First call: 401
        return Promise.resolve({
          ok: false,
          status: 401,
          statusText: "Unauthorized",
          json: () => Promise.resolve({ detail: "Token expired" }),
        });
      }
      // Retry call: success
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ id: "123", email: "test@test.com" }),
      });
    });

    vi.stubGlobal("fetch", mockFetch);
    vi.stubGlobal("localStorage", {
      getItem: vi.fn().mockReturnValue("expired-token"),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });

    const { getProfile } = await import("@/lib/api");
    const result = await getProfile();

    expect(result).toEqual({ id: "123", email: "test@test.com" });
    // Should have called: original request, refresh, retry
    expect(mockFetch).toHaveBeenCalledTimes(3);
    // Token should be saved
    expect(localStorage.setItem).toHaveBeenCalledWith("token", "new-token");
  });

  it("clears auth state when refresh also fails with 401", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: () => Promise.resolve({ detail: "Session expired" }),
    });

    vi.stubGlobal("fetch", mockFetch);
    vi.stubGlobal("localStorage", {
      getItem: vi.fn().mockReturnValue("expired-token"),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });

    const { getProfile } = await import("@/lib/api");
    await expect(getProfile()).rejects.toThrow("Session expired");
    expect(localStorage.removeItem).toHaveBeenCalledWith("token");
    expect(localStorage.removeItem).toHaveBeenCalledWith("user");
  });

  it("does not attempt refresh when no token exists", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: () => Promise.resolve({ detail: "Not authenticated" }),
    });

    vi.stubGlobal("fetch", mockFetch);
    vi.stubGlobal("localStorage", {
      getItem: vi.fn().mockReturnValue(null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });

    const { getProfile } = await import("@/lib/api");
    await expect(getProfile()).rejects.toThrow("Not authenticated");
    // Should only have made the one original request (no refresh attempt)
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });
});

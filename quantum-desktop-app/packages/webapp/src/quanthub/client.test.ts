import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./client";

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

describe("QuantHub client error reporting", () => {
  it("surfaces the server's own message for an unauthorized write", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            data: null,
            error: {
              code: "Unauthorized",
              message:
                "This QuantHub server requires a signed-in account, and local development sessions are disabled.",
            },
          },
          401,
        ),
      ),
    );

    await expect(api("/projects", { method: "POST", body: { name: "x" } })).rejects.toMatchObject({
      status: 401,
      code: "Unauthorized",
      message:
        "This QuantHub server requires a signed-in account, and local development sessions are disabled.",
    });
  });

  it("reports the HTTP status instead of a bare 'Request failed.' for non-JSON errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("<html>Bad gateway</html>", {
          status: 502,
          headers: { "Content-Type": "text/html" },
        }),
      ),
    );

    const failure = await api("/projects").catch((error: unknown) => error);
    expect(failure).toBeInstanceOf(ApiError);
    const error = failure as ApiError;
    expect(error.status).toBe(502);
    expect(error.message).toContain("502");
    // The raw upstream body is never shown to the user.
    expect(error.message).not.toContain("<html>");
    expect(error.message.toLowerCase()).not.toContain("request failed");
  });

  it("names the status for a bodiless 401 from an authenticating proxy", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("", { status: 401 })),
    );

    const failure = (await api("/projects").catch((error: unknown) => error)) as ApiError;
    expect(failure.status).toBe(401);
    expect(failure.message).toContain("401");
    expect(failure.message).toContain("Sign in");
  });

  it("still returns the data of a successful envelope", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ data: { id: "p_1" }, error: null }, 201)),
    );

    await expect(api<{ id: string }>("/projects", { method: "POST", body: {} })).resolves.toEqual({
      id: "p_1",
    });
  });
});

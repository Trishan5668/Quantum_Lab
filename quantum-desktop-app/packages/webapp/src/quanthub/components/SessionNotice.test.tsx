import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const sessionState: Record<string, unknown> = {};

vi.mock("../session", () => ({
  useSession: () => sessionState,
}));

vi.mock("../../auth/AuthProvider", () => ({
  useAuth: () => ({ firebaseReady: false, openLogin: () => undefined }),
}));

// Import after the mocks so the component picks up the stubbed hooks.
const { SessionNotice } = await import("./SessionNotice");

function setSession(overrides: Record<string, unknown>): void {
  for (const key of Object.keys(sessionState)) delete sessionState[key];
  Object.assign(sessionState, {
    viewer: { mode: "guest", authenticated: false },
    capabilities: { local_sessions: true, firebase: false },
    usingFirebase: false,
    readOnlySession: false,
    ...overrides,
  });
}

beforeEach(() => setSession({}));

describe("SessionNotice", () => {
  it("stays silent when the server accepts local sessions", () => {
    const { container } = render(<SessionNotice />);
    expect(container).toBeEmptyDOMElement();
  });

  it("stays silent for a signed-in user", () => {
    setSession({
      viewer: { mode: "authenticated", authenticated: true },
      capabilities: { local_sessions: false, firebase: true },
    });
    const { container } = render(<SessionNotice />);
    expect(container).toBeEmptyDOMElement();
  });

  it("explains a read-only server instead of letting writes fail with 401", () => {
    setSession({
      capabilities: { local_sessions: false, firebase: false },
      readOnlySession: true,
    });
    render(<SessionNotice />);

    const notice = screen.getByRole("status");
    expect(notice).toHaveTextContent(/read-only/i);
    expect(notice).toHaveTextContent("QUANTHUB_ENV=development");
    expect(notice).toHaveTextContent("QUANTHUB_TRUST_CLIENT_IDENTITY=1");
    // No secret or filesystem path leaks into the UI.
    expect(notice.textContent ?? "").not.toContain("/home/");
  });
});

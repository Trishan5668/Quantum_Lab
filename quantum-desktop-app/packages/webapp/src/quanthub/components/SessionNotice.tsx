import { useAuth } from "../../auth/AuthProvider";
import { useSession } from "../session";

/**
 * Explains a read-only session before the user fills in a form that the server
 * is guaranteed to reject.
 *
 * The API reports which identity mechanisms it accepts on `GET /me`
 * (`capabilities`). When neither verified Firebase tokens nor local
 * development sessions are available, every write returns `401`; showing that
 * reason up front is the difference between a fixable configuration problem
 * and a mystery "Request failed" toast.
 */
export function SessionNotice({ className = "" }: { className?: string }): JSX.Element | null {
  const { viewer, capabilities, usingFirebase, readOnlySession } = useSession();
  const auth = useAuth();

  if (!viewer || viewer.mode !== "guest") return null;
  if (readOnlySession) {
    return (
      <div className={`qh-notice ${className}`.trim()} role="status">
        <strong>This server is read-only right now.</strong> It accepts neither a
        signed-in Firebase account nor a local development session, so creating
        projects, saving files and running experiments will fail. To use
        QuantHub locally, start the API with{" "}
        <code>QUANTHUB_ENV=development QUANTHUB_TRUST_CLIENT_IDENTITY=1</code>, or
        configure <code>FIREBASE_PROJECT_ID</code> on the server and sign in.
      </div>
    );
  }
  if (capabilities?.firebase && !usingFirebase && auth.firebaseReady) {
    return (
      <div className={`qh-notice ${className}`.trim()} role="status">
        <strong>Sign in to make changes.</strong> You can browse public projects
        without an account, but creating projects and saving files needs a
        signed-in account.{" "}
        <button type="button" className="qh-btn qh-btn-sm" onClick={auth.openLogin}>
          Sign in
        </button>
      </div>
    );
  }
  return null;
}

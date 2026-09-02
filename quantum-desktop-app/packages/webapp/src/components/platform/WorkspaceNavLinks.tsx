import { Link } from "react-router-dom";

export function EditorNavLink(): JSX.Element {
  return (
    <Link
      to="/app/editor"
      className="workspace-tab hidden sm:inline-flex"
      title="Open quantum code editor"
    >
      Editor
    </Link>
  );
}

export function SimulatorNavLink(): JSX.Element {
  return (
    <Link
      to="/app"
      className="workspace-tab hidden sm:inline-flex"
      title="Return to circuit simulator"
    >
      Simulator
    </Link>
  );
}

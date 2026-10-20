import { Outlet } from "react-router-dom";
import { SessionProvider } from "../session";
import { QuantHubShell } from "./Shell";

export function QuantHubLayout(): JSX.Element {
  return (
    <SessionProvider>
      <QuantHubShell>
        <Outlet />
      </QuantHubShell>
    </SessionProvider>
  );
}

import { Outlet } from "react-router-dom";
import { GridBackground } from "./GridBackground";
import { PlatformFooter } from "./PlatformFooter";
import { PlatformNav } from "./PlatformNav";

export function PlatformLayout(): JSX.Element {
  return (
    <div className="platform-shell relative min-h-full overflow-x-hidden overflow-y-auto bg-bg-base text-text-primary">
      <GridBackground />
      <PlatformNav />
      <main className="relative z-10">
        <Outlet />
      </main>
      <PlatformFooter />
    </div>
  );
}

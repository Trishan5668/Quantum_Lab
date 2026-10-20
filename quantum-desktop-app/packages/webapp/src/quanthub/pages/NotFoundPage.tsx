import { Link } from "react-router-dom";
import { PageMeta } from "../../components/platform/PageMeta";

export default function NotFoundPage(): JSX.Element {
  return (
    <>
      <PageMeta title="Not found" description="This page does not exist on QuantHub." />
      <div className="qh-container py-16 text-center">
        <p className="qh-mono m-0 text-[48px] font-semibold text-[#30363d]">404</p>
        <h1 className="mb-2 mt-0 text-[20px] font-semibold">This page does not exist</h1>
        <p className="qh-subtle mx-auto max-w-md">
          The project or page may be private, archived, or renamed. QuantHub never redirects to a
          guessed project.
        </p>
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          <Link to="/" className="qh-btn qh-btn-primary">Home</Link>
          <Link to="/explore" className="qh-btn">Explore projects</Link>
          <Link to="/new" className="qh-btn">New project</Link>
        </div>
      </div>
    </>
  );
}

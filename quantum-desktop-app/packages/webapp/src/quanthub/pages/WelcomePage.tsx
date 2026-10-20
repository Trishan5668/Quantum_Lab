import { Link } from "react-router-dom";
import { PageMeta } from "../../components/platform/PageMeta";

const POINTS = [
  {
    title: "Projects, not repositories",
    body: "A project is the unit of work: files, circuits, experiment specifications and the evidence they produced.",
  },
  {
    title: "Evidence over adjectives",
    body: "Experiment runs are executed by the Python QEC engine in a resource-limited process and stored with checksums, provenance and an audit trail.",
  },
  {
    title: "No fabricated results",
    body: "QuantHub never invents projects, news items, validations or successful runs. Empty states are honest states.",
  },
  {
    title: "No AI requirement",
    body: "Browsing, editing, importing, simulating and running error-correction experiments work without API keys or a subscription.",
  },
];

export default function WelcomePage(): JSX.Element {
  return (
    <>
      <PageMeta title="About QuantHub" description="What QuantHub is and how it treats evidence." />
      <div className="qh-container max-w-[820px] py-8">
        <h1 className="mb-2 mt-0 text-[24px] font-semibold">About QuantHub</h1>
        <p className="mb-6 text-[14px] text-[#9198a1]">
          QuantHub is a project-centric platform for quantum software, experiments and reproducible
          research, built on the QuantumLab engine. It keeps the existing simulator, density-matrix
          and noise code and adds a GitHub-style workspace around it.
        </p>

        <div className="space-y-3">
          {POINTS.map((point) => (
            <section key={point.title} className="qh-card qh-card-body">
              <h2 className="m-0 text-[14px] font-semibold">{point.title}</h2>
              <p className="mb-0 mt-1 text-[13px] text-[#9198a1]">{point.body}</p>
            </section>
          ))}
        </div>

        <section className="qh-card qh-card-body mt-4">
          <h2 className="m-0 text-[14px] font-semibold">Scientific status dictionary</h2>
          <dl className="mt-2 grid gap-2 text-[12px] text-[#9198a1] sm:grid-cols-2">
            <div><dt className="font-semibold text-[#c9d1d9]">Configuration validated</dt><dd className="m-0">The engine accepted the protocol schema and decoder choices.</dd></div>
            <div><dt className="font-semibold text-[#c9d1d9]">Execution complete</dt><dd className="m-0">The engine process exited successfully and wrote artifacts.</dd></div>
            <div><dt className="font-semibold text-[#c9d1d9]">Integrity verified</dt><dd className="m-0">Checksums and manifest match the bytes on disk.</dd></div>
            <div><dt className="font-semibold text-[#c9d1d9]">Reproduced</dt><dd className="m-0">A rerun produced the same configuration; independent reproduction requires a third party.</dd></div>
            <div><dt className="font-semibold text-[#c9d1d9]">Peer reviewed</dt><dd className="m-0">Never claimed by QuantHub; review happens outside the platform.</dd></div>
          </dl>
        </section>

        <div className="mt-5 flex flex-wrap gap-2">
          <Link to="/new" className="qh-btn qh-btn-primary">New project</Link>
          <Link to="/explore" className="qh-btn">Explore</Link>
          <Link to="/docs" className="qh-btn">Documentation</Link>
        </div>
      </div>
    </>
  );
}

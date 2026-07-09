import { Link } from "react-router-dom";
import { PageMeta } from "../components/platform/PageMeta";
import { SectionHeader } from "../components/platform/SectionHeader";

export default function CommunityPage(): JSX.Element {
  return (
    <>
      <PageMeta title="Community" description="Join the QuantumLab open-source quantum computing community." />
      <div className="platform-container max-w-3xl py-12 sm:py-16">
        <SectionHeader
          eyebrow="Community"
          title="Quantum computing, together"
          subtitle="Students, educators, researchers, and builders — one open platform."
        />
        <div className="platform-card p-6">
          <p className="text-sm leading-relaxed text-text-secondary">
            QuantumLab is designed for university students, self-taught learners, and early-career quantum engineers.
            Report issues, suggest features, and contribute code or education content on GitHub.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="btn btn-primary btn-md">
              GitHub Discussions
            </a>
            <Link to="/opensource" className="btn btn-secondary btn-md">
              Contributing
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}

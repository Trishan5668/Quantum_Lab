import { Link } from "react-router-dom";
import { PageMeta } from "../components/platform/PageMeta";
import { SectionHeader } from "../components/platform/SectionHeader";

export default function CommunityPage(): JSX.Element {
  return (
    <>
      <PageMeta title="Community" description="Join the QuantumLab quantum computing learning community." />
      <div className="platform-container max-w-3xl py-12 sm:py-16">
        <SectionHeader
          eyebrow="Community"
          title="Quantum computing, together"
          subtitle="Students, educators, researchers, and builders — one learning platform."
        />
        <div className="platform-card p-6">
          <p className="text-sm leading-relaxed text-text-secondary">
            QuantumLab is designed for university students, self-taught learners, and early-career quantum engineers.
            Explore lessons, run experiments, and share quantum computing ideas with your learning community.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link to="/learn" className="btn btn-primary btn-md">
              Start Learning
            </Link>
            <Link to="/docs" className="btn btn-secondary btn-md">
              Read Docs
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}

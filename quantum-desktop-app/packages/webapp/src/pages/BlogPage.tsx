import { Link } from "react-router-dom";
import { PageMeta } from "../components/platform/PageMeta";
import { SectionHeader } from "../components/platform/SectionHeader";

const POSTS = [
  {
    slug: "platform-v1",
    title: "Introducing the QuantumLab Platform",
    date: "2026",
    summary: "One unified ecosystem: simulator, learning, algorithms, and documentation.",
  },
  {
    slug: "v2-density-noise",
    title: "QuantumLab v2: Density Matrices & Noise",
    date: "2026",
    summary: "Mixed-state simulation, Kraus channels, fidelity, and entanglement entropy.",
  },
] as const;

export default function BlogPage(): JSX.Element {
  return (
    <>
      <PageMeta title="Blog" description="QuantumLab platform updates and quantum computing insights." />
      <div className="platform-container max-w-3xl py-12 sm:py-16">
        <SectionHeader eyebrow="Blog" title="Updates & insights" subtitle="Platform news and quantum education." />
        <div className="space-y-4">
          {POSTS.map((post) => (
            <article key={post.slug} className="platform-card p-5">
              <p className="font-mono text-[10px] text-text-muted">{post.date}</p>
              <h3 className="mt-1 font-sans text-lg font-semibold">{post.title}</h3>
              <p className="mt-2 text-sm text-text-secondary">{post.summary}</p>
            </article>
          ))}
        </div>
        <Link to="/" className="btn btn-ghost btn-sm mt-8">
          ← Home
        </Link>
      </div>
    </>
  );
}

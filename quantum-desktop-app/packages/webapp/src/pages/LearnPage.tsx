import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { PageMeta } from "../components/platform/PageMeta";
import { SectionHeader } from "../components/platform/SectionHeader";
import { LEARNING_LAYERS } from "../store/platformStore";

export default function LearnPage(): JSX.Element {
  return (
    <>
      <PageMeta
        title="Learn Quantum Computing"
        description="Progressive disclosure learning — Explore, Understand, Intuition, and Research layers."
      />
      <div className="platform-container py-12 sm:py-16">
        <SectionHeader
          eyebrow="Learn"
          title="One simulator. Four depths."
          subtitle="Never switch applications — only reveal more as you're ready."
        />

        <div className="grid gap-4 lg:grid-cols-2">
          {LEARNING_LAYERS.map((layer, i) => (
            <motion.div
              key={layer.id}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08, duration: 0.4 }}
              className="platform-card p-6"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-display text-[10px] font-semibold uppercase tracking-[0.25em] text-accent-measure">
                    Layer {i + 1}
                  </p>
                  <h3 className="mt-1 font-sans text-xl font-semibold text-text-primary">
                    {layer.label}
                  </h3>
                  <p className="mt-1 text-sm text-accent-glow">{layer.tagline}</p>
                </div>
                <span className="font-mono text-3xl font-bold text-border">{i + 1}</span>
              </div>
              <p className="mt-4 text-sm leading-relaxed text-text-secondary">
                {layer.description}
              </p>
            </motion.div>
          ))}
        </div>

        <div className="mt-10 flex flex-wrap gap-3">
          <Link to="/app" className="btn btn-primary btn-md">
            Open Simulator
          </Link>
          <Link to="/algorithms" className="btn btn-secondary btn-md">
            Browse Algorithms
          </Link>
          <Link to="/docs" className="btn btn-ghost btn-md">
            Read Documentation
          </Link>
        </div>
      </div>
    </>
  );
}

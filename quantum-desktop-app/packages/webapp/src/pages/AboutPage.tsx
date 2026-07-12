import { motion } from "framer-motion";
import { PageMeta } from "../components/platform/PageMeta";
import { SectionHeader } from "../components/platform/SectionHeader";
import { CREATOR } from "../config/attribution";

const TOPICS = [
  "Quantum Mechanics",
  "Quantum Computing",
  "Linear Algebra",
  "Quantum Information",
  "State Vectors",
  "Density Matrices",
  "Bloch Sphere",
  "Tensor Products",
  "Entanglement",
  "Quantum Algorithms",
] as const;

const SIMULATION_FEATURES = [
  "Interactive visualizations",
  "Mathematical derivations",
  "Physics explanations",
  "AI-assisted learning",
] as const;

const PASSIONS = [
  "Quantum Computing",
  "Quantum Mechanics",
  "Educational Software",
  "Scientific Visualization",
  "AI-assisted Learning",
] as const;

export default function AboutPage(): JSX.Element {
  return (
    <>
      <PageMeta
        title="About QuantumLab"
        description="QuantumLab is an educational quantum computing platform for interactive visualization, mathematical derivation, physics explanation, and AI-assisted learning."
      />

      <section className="platform-container py-16 sm:py-20">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,1.4fr)_minmax(18rem,0.8fr)] lg:items-start">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
          >
            <p className="mb-3 font-display text-[10px] font-semibold uppercase tracking-[0.3em] text-accent-measure">
              About
            </p>
            <h1 className="font-sans text-4xl font-semibold tracking-tight text-text-primary sm:text-5xl">
              QuantumLab
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-relaxed text-text-secondary sm:text-lg">
              QuantumLab is an educational quantum computing platform focused on helping students
              understand the mathematical and physical structure behind quantum systems.
            </p>
          </motion.div>

          <CreatorCard />
        </div>
      </section>

      <section className="border-y border-border/60 bg-bg-surface/30 py-14 sm:py-16">
        <div className="platform-container">
          <SectionHeader
            eyebrow="Learning focus"
            title="Built for quantum education"
            subtitle="The platform connects visual intuition with the algebra and physics students need for deeper understanding."
          />
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {TOPICS.map((topic) => (
              <div key={topic} className="platform-card px-4 py-3 text-sm text-text-secondary">
                {topic}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="platform-container py-14 sm:py-16">
        <SectionHeader
          eyebrow="Every simulation"
          title="From circuit behavior to explanation"
          subtitle="Each run is designed to make the result inspectable, traceable, and teachable."
        />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {SIMULATION_FEATURES.map((feature) => (
            <div key={feature} className="platform-card p-5">
              <p className="font-display text-xs font-semibold uppercase tracking-[0.18em] text-accent-glow">
                {feature}
              </p>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

function CreatorCard(): JSX.Element {
  return (
    <motion.aside
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay: 0.08 }}
      className="platform-card p-5"
    >
      <p className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
        Creator
      </p>
      <div className="mt-4">
        <h2 className="font-sans text-xl font-semibold text-text-primary">{CREATOR.name}</h2>
        <p className="mt-1 text-sm text-text-secondary">Student Researcher</p>
        <p className="text-sm text-text-secondary">Open Source Developer</p>
      </div>

      <div className="mt-5">
        <p className="font-display text-[10px] font-semibold uppercase tracking-[0.2em] text-accent-measure">
          Passionate about
        </p>
        <ul className="mt-3 grid gap-2 text-sm text-text-secondary">
          {PASSIONS.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>

      <div className="mt-5 border-t border-border/70 pt-5">
        <p className="font-display text-[10px] font-semibold uppercase tracking-[0.2em] text-accent-measure">
          Contact
        </p>
        <div className="mt-3 grid gap-2 text-sm text-text-muted">
          <a href={`mailto:${CREATOR.email}`} className="break-all hover:text-text-primary">
            {CREATOR.email}
          </a>
          <a href={CREATOR.instagram} target="_blank" rel="noopener noreferrer" className="hover:text-text-primary">
            Instagram
          </a>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <a href={`mailto:${CREATOR.email}`} className="btn btn-primary btn-sm">
            Email
          </a>
          <a href={CREATOR.instagram} target="_blank" rel="noopener noreferrer" className="btn btn-secondary btn-sm">
            Instagram
          </a>
        </div>
      </div>
    </motion.aside>
  );
}


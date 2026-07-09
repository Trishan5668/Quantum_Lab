import { motion } from "framer-motion";
import type { ReactNode } from "react";

interface SectionHeaderProps {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  children?: ReactNode;
}

export function SectionHeader({
  eyebrow,
  title,
  subtitle,
  children,
}: SectionHeaderProps): JSX.Element {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.45, ease: "easeOut" }}
      className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"
    >
      <div className="max-w-2xl">
        {eyebrow && (
          <p className="mb-2 font-display text-[10px] font-semibold uppercase tracking-[0.25em] text-accent-measure">
            {eyebrow}
          </p>
        )}
        <h2 className="font-sans text-2xl font-semibold tracking-tight text-text-primary sm:text-3xl">
          {title}
        </h2>
        {subtitle && (
          <p className="mt-2 text-sm leading-relaxed text-text-secondary sm:text-base">
            {subtitle}
          </p>
        )}
      </div>
      {children}
    </motion.div>
  );
}

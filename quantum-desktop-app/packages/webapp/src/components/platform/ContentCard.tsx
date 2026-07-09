import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";

interface ContentCardProps {
  title: string;
  description: string;
  to?: string;
  href?: string;
  badge?: string;
  children?: ReactNode;
}

export function ContentCard({
  title,
  description,
  to,
  href,
  badge,
  children,
}: ContentCardProps): JSX.Element {
  const inner = (
    <motion.article
      whileHover={{ y: -2 }}
      transition={{ duration: 0.2 }}
      className="platform-card group flex h-full flex-col p-5"
    >
      {badge && (
        <span className="mb-3 inline-flex w-fit rounded-full bg-accent-quantum/10 px-2 py-0.5 font-mono text-[10px] text-accent-glow ring-1 ring-accent-quantum/25">
          {badge}
        </span>
      )}
      <h3 className="font-sans text-base font-semibold text-text-primary group-hover:text-accent-glow">
        {title}
      </h3>
      <p className="mt-2 flex-1 text-sm leading-relaxed text-text-secondary">{description}</p>
      {children}
      {(to || href) && (
        <span className="mt-4 font-mono text-[10px] text-accent-measure group-hover:underline">
          Open →
        </span>
      )}
    </motion.article>
  );

  if (to) {
    return (
      <Link to={to} className="block h-full focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-quantum/50 rounded-lg">
        {inner}
      </Link>
    );
  }
  if (href) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="block h-full focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-quantum/50 rounded-lg"
      >
        {inner}
      </a>
    );
  }
  return inner;
}

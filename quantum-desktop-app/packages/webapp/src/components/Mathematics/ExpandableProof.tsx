import type { ReactNode } from "react";

interface ExpandableProofProps {
  title: string;
  subtitle?: string;
  defaultOpen?: boolean;
  children: ReactNode;
}

export function ExpandableProof({
  title,
  subtitle,
  defaultOpen = false,
  children,
}: ExpandableProofProps): JSX.Element {
  return (
    <details className="math-proof" open={defaultOpen}>
      <summary className="math-proof-summary">
        <span className="min-w-0">
          <span className="block truncate font-mono text-[11px] font-semibold text-text-primary">{title}</span>
          {subtitle && <span className="block truncate text-[11px] text-text-muted">{subtitle}</span>}
        </span>
        <span className="math-why">Why?</span>
      </summary>
      <div className="math-proof-body">{children}</div>
    </details>
  );
}

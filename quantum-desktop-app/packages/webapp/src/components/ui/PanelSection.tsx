import type { ReactNode } from "react";

interface PanelSectionProps {
  title: string;
  subtitle?: string;
  badge?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  noBorder?: boolean;
}

/** Consistent panel chrome used across visualization and control surfaces. */
export function PanelSection({
  title,
  subtitle,
  badge,
  actions,
  children,
  className = "",
  noBorder = false,
}: PanelSectionProps): JSX.Element {
  return (
    <section
      className={`panel-section ${noBorder ? "" : "border-b border-border"} ${className}`}
    >
      <header className="panel-header">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="panel-title">{title}</h2>
            {badge}
          </div>
          {subtitle && <p className="panel-subtitle">{subtitle}</p>}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-1.5">{actions}</div>}
      </header>
      <div className="panel-body">{children}</div>
    </section>
  );
}

export function PanelPlaceholder({ children }: { children: ReactNode }): JSX.Element {
  return <div className="panel-placeholder">{children}</div>;
}

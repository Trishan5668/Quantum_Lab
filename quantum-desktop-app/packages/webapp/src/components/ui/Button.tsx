import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: "sm" | "md";
  loading?: boolean;
  children: ReactNode;
}

const variantClass: Record<ButtonVariant, string> = {
  primary: "btn-primary",
  secondary: "btn-secondary",
  ghost: "btn-ghost",
  danger: "btn-danger",
};

export function Button({
  variant = "secondary",
  size = "sm",
  loading = false,
  disabled,
  className = "",
  children,
  ...rest
}: ButtonProps): JSX.Element {
  return (
    <button
      type="button"
      disabled={disabled || loading}
      className={`btn ${variantClass[variant]} ${size === "md" ? "btn-md" : "btn-sm"} ${className}`}
      {...rest}
    >
      {loading ? (
        <span className="inline-flex items-center gap-1.5">
          <span className="btn-spinner" aria-hidden />
          {children}
        </span>
      ) : (
        children
      )}
    </button>
  );
}

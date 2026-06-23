declare module "react-katex" {
  import type { ComponentType } from "react";

  export interface MathProps {
    math: string;
    errorColor?: string;
    renderError?: (error: Error) => JSX.Element;
  }

  export const InlineMath: ComponentType<MathProps>;
  export const BlockMath: ComponentType<MathProps>;
}

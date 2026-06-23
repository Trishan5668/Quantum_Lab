/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: {
          base: "var(--bg-base)",
          surface: "var(--bg-surface)",
          elevated: "var(--bg-elevated)",
        },
        accent: {
          quantum: "var(--accent-quantum)",
          glow: "var(--accent-glow)",
          measure: "var(--accent-measure)",
          warn: "var(--accent-warn)",
        },
        text: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
        },
        border: {
          DEFAULT: "var(--border)",
        },
        gate: {
          h: "var(--gate-h)",
          xyz: "var(--gate-xyz)",
          rot: "var(--gate-rot)",
          cnot: "var(--gate-cnot)",
          measure: "var(--gate-measure)",
        },
      },
      fontFamily: {
        display: ["'JetBrains Mono'", "ui-monospace", "monospace"],
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      animation: {
        "wire-pulse": "wire-pulse 400ms ease-out forwards",
        "neon-border": "neon-border 1.4s ease-in-out infinite",
      },
      keyframes: {
        "wire-pulse": {
          "0%": { transform: "translateX(-30%)", opacity: "0" },
          "30%": { opacity: "1" },
          "100%": { transform: "translateX(120%)", opacity: "0" },
        },
        "neon-border": {
          "0%,100%": { boxShadow: "0 0 0 0 rgba(124, 58, 237, 0)" },
          "50%": { boxShadow: "0 0 18px 1px rgba(124, 58, 237, 0.6)" },
        },
      },
    },
  },
  plugins: [],
};

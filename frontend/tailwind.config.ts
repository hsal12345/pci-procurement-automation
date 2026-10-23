import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",

        // Pustaka Cemerlang Official Brand Tokens
        pci: {
          blue: {
            DEFAULT: "#02569D",
            50: "#eaf3fa",
            100: "#c7e0f5",
            200: "#9ec5ec",
            300: "#6aa5e3",
            400: "#3684d7",
            500: "#02569D",
            600: "#024a87",
            700: "#013a6b",
            800: "#012d53",
            900: "#021322",
          },
          orange: {
            DEFAULT: "#FE6307",
            50: "#fff5ed",
            100: "#ffe7d4",
            200: "#ffcca9",
            300: "#ffa873",
            400: "#fe7e35",
            500: "#FE6307",
            600: "#dc4c02",
            700: "#b03604",
            800: "#8c2c0a",
            900: "#73260c",
          },
          navy: "#021322",
          rose: "#E22658",
          green: "#259655",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      boxShadow: {
        "pci-sm": "0 2px 4px 0 rgba(2, 86, 157, 0.08)",
        "pci-md": "0 4px 12px 0 rgba(2, 86, 157, 0.12)",
        "pci-lg": "0 8px 24px -4px rgba(2, 86, 157, 0.18)",
      },
    },
  },
  plugins: [],
};

export default config;
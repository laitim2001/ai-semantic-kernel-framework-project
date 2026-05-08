/**
 * File: frontend/tailwind.config.ts
 * Purpose: Tailwind CSS v4 configuration — content paths + theme + dark mode strategy.
 * Category: Frontend / build config
 * Scope: Phase 57 / Sprint 57.7 US-B1 (Frontend Foundation 1/N install)
 *
 * Modification History:
 *   - 2026-05-09: Initial creation (Sprint 57.7 US-B1 Day 2 PM)
 */

import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class", // toggle via html.dark — ThemeProvider US-B2 Day 3
  theme: {
    extend: {
      colors: {
        // shadcn CSS variable bridge — actual values set in src/index.css
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [],
};

export default config;

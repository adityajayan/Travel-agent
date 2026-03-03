import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    borderRadius: {
      none: "0",
      DEFAULT: "0",
      sm: "0",
      md: "0",
      lg: "0",
      xl: "0",
      "2xl": "0",
      "3xl": "0",
      full: "0",
    },
    extend: {
      colors: {
        paper: "#f8f5ef",
        "paper-elevated": "#f0ede6",
        contrast: "#1a1a1a",
        accent: {
          DEFAULT: "#c0392b",
          soft: "rgba(192, 57, 43, 0.08)",
          border: "rgba(192, 57, 43, 0.2)",
        },
        success: {
          DEFAULT: "#1a7a4c",
          soft: "rgba(26, 122, 76, 0.08)",
          border: "rgba(26, 122, 76, 0.2)",
        },
        "text-primary": "#1a1a1a",
        "text-mid": "#3d3d3d",
        "text-muted": "#777777",
        "text-ghost": "#aaaaaa",
        "border-heavy": "#1a1a1a",
        "border-light": "#e0dbd3",
      },
      fontFamily: {
        display: ['"Playfair Display"', "Georgia", "serif"],
        ui: ['"Syne"', "system-ui", "sans-serif"],
        body: ['"DM Sans"', "system-ui", "sans-serif"],
        quote: ['"Lora"', "Georgia", "serif"],
      },
      boxShadow: {
        "hard-sm": "4px 4px 0 #1a1a1a",
        hard: "8px 8px 0 #1a1a1a",
      },
      animation: {
        "fade-up": "fadeUp 0.6s ease-out forwards",
        "fade-up-delay-1": "fadeUp 0.6s ease-out 0.08s forwards",
        "fade-up-delay-2": "fadeUp 0.6s ease-out 0.16s forwards",
        "fade-up-delay-3": "fadeUp 0.6s ease-out 0.24s forwards",
        "fade-up-delay-4": "fadeUp 0.6s ease-out 0.35s forwards",
        "slide-in-right": "slideInRight 0.5s ease-out forwards",
        shimmer: "shimmer 2s ease-in-out infinite",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(22px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideInRight: {
          "0%": { opacity: "0", transform: "translateX(20px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
};

export default config;

import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        blackDeep: "#18241d",
        cream: "#f4ecdd",
        "cream-2": "#efe4d0",
        paper: "#fbf7ee",
        "paper-2": "#fffdf8",
        ink: "#18241d",
        "ink-soft": "#51605a",
        "ink-faint": "#8a948e",
        green: "#0e9f6e",
        "green-deep": "#0b7d57",
        "green-dark": "#0d3a2a",
        "green-ink": "#0e4a37",
        terracotta: "#d9714e",
        bronze: "#c25c3c",
        marigold: "#86d9b4",
        gold: "#f5b63f",
        card: "#fbf7ee",
        borderSoft: "rgba(24,36,29,0.10)",
      },
      borderRadius: {
        card: "16px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(20,40,30,0.05), 0 18px 40px -24px rgba(20,40,30,0.35)",
      },
      fontFamily: {
        serif: ['"Newsreader"', "Georgia", "serif"],
        kn: ['"Noto Serif Kannada"', '"Newsreader"', "serif"],
      },
    },
  },
  plugins: [],
};

export default config;

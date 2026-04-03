/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          300: "#93c5fd",
          400: "#60a5fa",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "Fira Code", "Cascadia Code", "monospace"],
      },
      animation: {
        "fade-in":  "fadeIn 0.2s ease-out",
        "slide-in": "slideIn 0.2s ease-out",
        "shake":    "shake 0.35s ease-in-out",
        "drawer-in":"drawerIn 0.2s ease-out",
        "shimmer":  "shimmer 1.6s linear infinite",
      },
      keyframes: {
        fadeIn:   { from: { opacity: 0 },                        to: { opacity: 1 } },
        slideIn:  { from: { opacity: 0, transform: "translateY(4px)" }, to: { opacity: 1, transform: "translateY(0)" } },
        shake: {
          "0%, 100%": { transform: "translateX(0)" },
          "20%, 60%": { transform: "translateX(-4px)" },
          "40%, 80%": { transform: "translateX(4px)" },
        },
        drawerIn: { from: { transform: "translateX(-100%)" }, to: { transform: "translateX(0)" } },
        shimmer: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
};

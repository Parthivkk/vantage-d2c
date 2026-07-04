/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          900: "#09090b", // Rich near-black
          800: "#18181b", // Deep charcoal
          700: "#27272a", // Medium zinc
          600: "#3f3f46", // Light zinc
        },
        gold: {
          50: "#fdfdf0",
          100: "#fbfbe0",
          200: "#f7f7c1",
          300: "#f3f3a2",
          400: "#efef83",
          500: "#d97706", // Amber gold
          600: "#b45309",
          700: "#78350f",
          800: "#451a03",
          900: "#180800",
        }
      },
      fontFamily: {
        sans: ["Outfit", "Inter", "sans-serif"],
      }
    },
  },
  plugins: [],
}

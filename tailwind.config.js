/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {},
    colors: {
      "primary-color": "var(--primary-color)",
      "surface-hover": "var(--surface-hover)",
      "surface-ground": "var(--surface-ground)",
    },
    borderRadius: {
      DEFAULT: "var(--border-radius)",
    },
    boxShadow: {
      focus: "var(--focus-ring)",
    },
  },
  plugins: [],
};

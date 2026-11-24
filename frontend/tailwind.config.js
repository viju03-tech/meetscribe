/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0B0B0E",
        surface: "#121216",
        elevated: "#18181E",
        crimson: "#D9384D",
        crimsonHover: "#F05A6C",
        ink: "#F4F1F2",
        muted: "#929099",
        border: "#292930",
      },
    },
  },
  plugins: [],
};

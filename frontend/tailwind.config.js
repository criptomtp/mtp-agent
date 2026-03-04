/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        mtp: {
          blue: "#1B3A6B",
          orange: "#E8730A",
        },
      },
    },
  },
  plugins: [],
};

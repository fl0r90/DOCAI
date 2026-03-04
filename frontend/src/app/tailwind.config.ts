import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        forensic: {
          900: '#020617',
          800: '#0f172a',
          700: '#1e293b',
          blue: '#3b82f6'
        }
      }
    },
  },
  plugins: [],
};
export default config;

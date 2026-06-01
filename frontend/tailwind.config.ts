import type { Config } from "tailwindcss"

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      boxShadow: {
        panel: "0 18px 48px rgba(15, 23, 42, 0.08)",
      },
    },
  },
  plugins: [],
}

export default config

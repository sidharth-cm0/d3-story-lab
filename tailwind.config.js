/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  corePlugins: {
    // Disable preflight to preserve hand-crafted editorial styles and component styling
    preflight: false,
  },
  theme: {
    extend: {
      colors: {
        d3: {
          void: '#050507',
          bg: '#0a0a0c',
          surface: '#121417',
          elevated: '#181b20',
          border: '#252830',
          amber: '#d4af37',
          'amber-soft': 'rgba(212, 175, 55, 0.15)',
          text: '#f5f3ef',
          muted: '#b5aea3',
          dim: '#7a736a',
        },
      },
      fontFamily: {
        display: ['"Barlow Condensed"', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
        serif: ['"Fraunces"', 'serif'],
        sans: ['"Archivo"', 'sans-serif'],
      },
      letterSpacing: {
        editorial: '0.2em',
        kicker: '0.15em',
      },
    },
  },
  plugins: [],
};

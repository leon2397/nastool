/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        dark: '#0d1117',
        panel: '#161b22',
        border: '#30363d',
        accent: '#58a6ff',
        success: '#3fb950',
        warning: '#d29922',
        danger: '#f85149',
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Helvetica Neue', 'Arial', 'sans-serif'],
      },
      borderRadius: {
        'card': '8px',
        'container': '12px',
      },
    },
  },
  plugins: [],
}

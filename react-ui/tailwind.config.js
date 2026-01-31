/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ['Outfit', 'sans-serif'],
        body: ['Manrope', 'sans-serif'],
        mono: ['Space Mono', 'monospace'],
        nephilim: ['Orbitron', 'Outfit', 'sans-serif'],
      },
      colors: {
        // NEPHILIM Core Palette
        nephilim: {
          void: '#0B0B0D',
          abyss: '#0d0a1a',
          deep: '#1a0f2e',
          surface: '#2a1745',
          cyan: '#00ffff',
          magenta: '#ff00ff',
          gold: '#ffd700',
          crimson: '#ff4500',
          electric: '#7b68ee',
        },
        // NEPHILIM Persona Colors
        eeva: {
          primary: '#e0c3fc',
          secondary: '#c4a7e7',
          DEFAULT: '#e0c3fc',
        },
        aegis: {
          primary: '#4a90d9',
          secondary: '#6ba3e0',
          DEFAULT: '#4a90d9',
        },
        solace: {
          primary: '#7eb8da',
          secondary: '#5eaed3',
          DEFAULT: '#7eb8da',
        },
        nyx: {
          primary: '#9b59b6',
          secondary: '#8e44ad',
          neon: '#ff00ff',
          DEFAULT: '#9b59b6',
        },
        cipher: {
          primary: '#2ecc71',
          secondary: '#27ae60',
          DEFAULT: '#2ecc71',
        },
        aurora: {
          primary: '#f39c12',
          secondary: '#e67e22',
          DEFAULT: '#f39c12',
        },
      },
      backgroundImage: {
        // NEPHILIM Gradients
        'nephilim-gradient': 'linear-gradient(135deg, #0B0B0D 0%, #1a0f2e 50%, #0B0B0D 100%)',
        'nephilim-radial': 'radial-gradient(ellipse at center, #1a0f2e 0%, #0B0B0D 70%)',
        'nephilim-cyan-magenta': 'linear-gradient(135deg, #00ffff, #ff00ff)',
        'nephilim-glow': 'radial-gradient(ellipse at 50% 50%, rgba(0, 255, 255, 0.15), transparent 70%)',
        // Persona Gradients
        'eeva-gradient': 'linear-gradient(135deg, #e0c3fc, #c4a7e7)',
        'aegis-gradient': 'linear-gradient(135deg, #4a90d9, #6ba3e0)',
        'solace-gradient': 'linear-gradient(135deg, #7eb8da, #5eaed3)',
        'nyx-gradient': 'linear-gradient(135deg, #9b59b6, #ff00ff)',
        'cipher-gradient': 'linear-gradient(135deg, #2ecc71, #27ae60)',
        'aurora-gradient': 'linear-gradient(135deg, #f39c12, #e67e22)',
      },
      boxShadow: {
        'nephilim-cyan': '0 0 20px rgba(0, 255, 255, 0.4)',
        'nephilim-magenta': '0 0 20px rgba(255, 0, 255, 0.4)',
        'nephilim-gold': '0 0 20px rgba(255, 215, 0, 0.4)',
        'nephilim-glow': '0 0 40px rgba(0, 255, 255, 0.2), 0 0 80px rgba(255, 0, 255, 0.1)',
        'eeva': '0 0 20px rgba(224, 195, 252, 0.5)',
        'aegis': '0 0 20px rgba(74, 144, 217, 0.5)',
        'solace': '0 0 20px rgba(126, 184, 218, 0.5)',
        'nyx': '0 0 20px rgba(155, 89, 182, 0.5)',
        'cipher': '0 0 20px rgba(46, 204, 113, 0.5)',
        'aurora': '0 0 20px rgba(243, 156, 18, 0.5)',
      },
      animation: {
        'nephilim-pulse': 'nephilim-pulse 3s ease-in-out infinite',
        'nephilim-flicker': 'nephilim-flicker 4s ease-in-out infinite',
        'nephilim-float': 'nephilim-float 6s ease-in-out infinite',
        'nephilim-glow': 'nephilim-glow 2s ease-in-out infinite',
        'nephilim-scan': 'nephilim-scan 8s linear infinite',
      },
      keyframes: {
        'nephilim-pulse': {
          '0%, 100%': { opacity: '1', filter: 'brightness(1)' },
          '50%': { opacity: '0.8', filter: 'brightness(1.2)' },
        },
        'nephilim-flicker': {
          '0%, 100%': { opacity: '1' },
          '92%': { opacity: '1' },
          '93%': { opacity: '0.8' },
          '94%': { opacity: '1' },
          '96%': { opacity: '0.9' },
          '97%': { opacity: '1' },
        },
        'nephilim-float': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'nephilim-glow': {
          '0%, 100%': { boxShadow: '0 0 20px rgba(0, 255, 255, 0.4)' },
          '50%': { boxShadow: '0 0 40px rgba(0, 255, 255, 0.6), 0 0 60px rgba(255, 0, 255, 0.3)' },
        },
        'nephilim-scan': {
          '0%': { backgroundPosition: '0% 0%' },
          '100%': { backgroundPosition: '0% 100%' },
        },
      },
      borderRadius: {
        'nephilim': '4px',
      },
      letterSpacing: {
        'nephilim': '0.1em',
        'nephilim-wide': '0.2em',
      },
    },
  },
  plugins: [],
}

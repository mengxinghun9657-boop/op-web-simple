/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      // 颜色系统 - 与 unified-design-system.css 保持同步（Google Blue 体系）
      colors: {
        // 主色 - Google Blue
        primary: {
          50:  '#e8f0fe',
          100: '#d2e3fc',
          200: '#aecbfa',
          300: '#8ab4f8',
          400: '#669df6',
          500: '#4285f4',
          DEFAULT: '#1a73e8',
          600: '#1a73e8',
          700: '#1967d2',
          800: '#185abc',
          900: '#174ea6',
        },
        // 次要色 - 青色（与设计系统 --color-secondary 对齐）
        secondary: {
          50:  '#ecfeff',
          100: '#cffafe',
          200: '#a5f3fc',
          300: '#67e8f9',
          400: '#22d3ee',
          500: '#06b6d4',
          DEFAULT: '#06b6d4',
          600: '#0891b2',
          700: '#0e7490',
          800: '#155e75',
          900: '#164e63',
        },
        // 中性色 - Google Gray（与 --color-neutral-* 对齐）
        neutral: {
          50:  '#f8f9fa',
          100: '#f1f3f4',
          200: '#e8eaed',
          300: '#dadce0',
          400: '#bdc1c6',
          500: '#9aa0a6',
          600: '#80868b',
          700: '#5f6368',
          800: '#3c4043',
          900: '#202124',
        },
        // 语义色 - 与 --color-success/warning/error 对齐
        success: {
          light: '#81c995',
          DEFAULT: '#1e8e3e',
          dark: '#137333',
        },
        warning: {
          light: '#fdd663',
          DEFAULT: '#f9ab00',
          dark: '#e37400',
        },
        error: {
          light: '#f28b82',
          DEFAULT: '#d93025',
          dark: '#b31412',
        },
        info: {
          light: '#8ab4f8',
          DEFAULT: '#1a73e8',
          dark: '#1967d2',
        },
        // 背景色（浅色主题，与 --bg-* 对齐）
        bg: {
          primary:   '#ffffff',
          secondary: '#f8f9fa',
          tertiary:  '#f1f3f4',
        },
      },
      // 间距系统 - 4px 基准（与 --space-* 对齐）
      spacing: {
        '0.5': '2px',
        '1': '4px',
        '1.5': '6px',
        '2': '8px',
        '2.5': '10px',
        '3': '12px',
        '3.5': '14px',
        '4': '16px',
        '5': '20px',
        '6': '24px',
        '7': '28px',
        '8': '32px',
        '9': '36px',
        '10': '40px',
        '11': '44px',
        '12': '48px',
        '14': '56px',
        '16': '64px',
        '18': '72px',
        '20': '80px',
        '24': '96px',
      },
      // 字体大小（与 --text-* 对齐）
      fontSize: {
        'xs':   ['11px', { lineHeight: '16px' }],
        'sm':   ['12px', { lineHeight: '18px' }],
        'base': ['14px', { lineHeight: '21px' }],
        'lg':   ['16px', { lineHeight: '24px' }],
        'xl':   ['18px', { lineHeight: '28px' }],
        '2xl':  ['22px', { lineHeight: '32px' }],
        '3xl':  ['28px', { lineHeight: '36px' }],
        '4xl':  ['34px', { lineHeight: '40px' }],
        '5xl':  ['40px', { lineHeight: '1' }],
      },
      // 圆角（与 --radius-* 对齐）
      borderRadius: {
        'none':  '0',
        'sm':    '4px',
        'DEFAULT': '8px',
        'md':    '8px',
        'lg':    '12px',
        'xl':    '16px',
        '2xl':   '20px',
        'full':  '9999px',
      },
      // 阴影系统（与 --shadow-* 对齐）
      boxShadow: {
        'sm':  '0 1px 2px rgba(60, 64, 67, 0.3), 0 1px 3px 1px rgba(60, 64, 67, 0.15)',
        'DEFAULT': '0 1px 3px rgba(60, 64, 67, 0.3), 0 4px 8px 3px rgba(60, 64, 67, 0.15)',
        'md':  '0 1px 3px rgba(60, 64, 67, 0.3), 0 4px 8px 3px rgba(60, 64, 67, 0.15)',
        'lg':  '0 2px 6px 2px rgba(60, 64, 67, 0.15), 0 8px 16px 4px rgba(60, 64, 67, 0.15)',
        'xl':  '0 4px 12px 4px rgba(60, 64, 67, 0.15), 0 12px 24px 8px rgba(60, 64, 67, 0.15)',
        'inner': 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.05)',
        'glass':    '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        'glass-sm': '0 4px 16px 0 rgba(0, 0, 0, 0.25)',
        'glass-lg': '0 12px 48px 0 rgba(0, 0, 0, 0.45)',
        'glow':         '0 0 0 3px rgba(26, 115, 232, 0.2)',
        'glow-sm':      '0 0 0 3px rgba(26, 115, 232, 0.15)',
        'glow-success': '0 0 0 3px rgba(30, 142, 62, 0.2)',
        'glow-warning': '0 0 0 3px rgba(249, 171, 0, 0.2)',
        'glow-error':   '0 0 0 3px rgba(217, 48, 37, 0.2)',
      },
      // 背景渐变
      backgroundImage: {
        'tech-gradient':  'linear-gradient(135deg, #1a73e8 0%, #06b6d4 100%)',
        'accent-gradient':'linear-gradient(135deg, #06b6d4 0%, #1e8e3e 100%)',
        'glass-gradient': 'linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%)',
      },
      // 动画
      animation: {
        'pulse-fast': 'pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in':    'fadeIn 0.2s ease-out',
        'fade-out':   'fadeOut 0.15s ease-in',
        'slide-up':   'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'scale-in':   'scaleIn 0.2s ease-out',
        'shimmer':    'shimmer 2s infinite linear',
      },
      keyframes: {
        fadeIn:    { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        fadeOut:   { '0%': { opacity: '1' }, '100%': { opacity: '0' } },
        slideUp:   { '0%': { opacity: '0', transform: 'translateY(10px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
        slideDown: { '0%': { opacity: '0', transform: 'translateY(-10px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
        scaleIn:   { '0%': { opacity: '0', transform: 'scale(0.95)' }, '100%': { opacity: '1', transform: 'scale(1)' } },
        shimmer:   { '0%': { backgroundPosition: '-200% 0' }, '100%': { backgroundPosition: '200% 0' } },
      },
      // 过渡时长（与 --duration-* 对齐）
      transitionDuration: {
        'fast':   '100ms',
        'normal': '200ms',
        'slow':   '300ms',
      },
      // 背景模糊
      backdropBlur: {
        'xs': '2px', 'sm': '4px', 'DEFAULT': '8px',
        'md': '12px', 'lg': '16px', 'xl': '24px',
        '2xl': '40px', '3xl': '64px',
      },
      // Z-index 层级（与 --z-* 对齐）
      zIndex: {
        'dropdown':       '1000',
        'sticky':         '1020',
        'fixed':          '1030',
        'modal-backdrop': '1040',
        'modal':          '1050',
        'popover':        '1060',
        'tooltip':        '1070',
        'toast':          '1080',
      },
    },
  },
  plugins: [],
}
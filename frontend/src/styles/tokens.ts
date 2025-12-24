// Rainbet-inspired design system tokens
// Dark mode aesthetic with slate grays and emerald accents

export const colors = {
    // Backgrounds
    background: '#0f1419',      // Near black
    surface: '#1a1f26',         // Dark slate
    surfaceHover: '#242b35',    // Lighter slate
    surfaceActive: '#2d3544',   // Active/pressed state

    // Borders
    border: '#2d3748',          // Subtle border
    borderLight: '#3d4758',     // Lighter border for hover states

    // Text
    text: '#e2e8f0',            // Light gray text
    textMuted: '#718096',       // Muted text
    textDim: '#4a5568',         // Very dim text

    // Primary (Emerald green - positive/success)
    primary: '#10b981',         // Emerald green
    primaryHover: '#059669',    // Darker emerald
    primaryLight: '#34d399',    // Lighter emerald
    primaryGlow: 'rgba(16, 185, 129, 0.2)', // Glow effect

    // Danger (Red - negative/exit warning)
    danger: '#ef4444',          // Red
    dangerHover: '#dc2626',     // Darker red
    dangerLight: '#f87171',     // Lighter red
    dangerGlow: 'rgba(239, 68, 68, 0.2)', // Glow effect

    // Warning (Amber - caution)
    warning: '#f59e0b',         // Amber
    warningHover: '#d97706',    // Darker amber
    warningLight: '#fbbf24',    // Lighter amber

    // Accent (Indigo - secondary actions)
    accent: '#6366f1',          // Indigo
    accentHover: '#4f46e5',     // Darker indigo
    accentLight: '#818cf8',     // Lighter indigo

    // Card suits
    cardRed: '#ef4444',         // Hearts and Diamonds
    cardBlack: '#e2e8f0',       // Spades and Clubs
};

export const spacing = {
    xs: '0.25rem',   // 4px
    sm: '0.5rem',    // 8px
    md: '1rem',      // 16px
    lg: '1.5rem',    // 24px
    xl: '2rem',      // 32px
    '2xl': '3rem',   // 48px
    '3xl': '4rem',   // 64px
};

export const borderRadius = {
    sm: '0.375rem',  // 6px
    md: '0.5rem',    // 8px
    lg: '0.75rem',   // 12px
    xl: '1rem',      // 16px
    full: '9999px',  // Pill shape
};

export const fontSize = {
    xs: '0.75rem',   // 12px
    sm: '0.875rem',  // 14px
    base: '1rem',    // 16px
    lg: '1.125rem',  // 18px
    xl: '1.25rem',   // 20px
    '2xl': '1.5rem', // 24px
    '3xl': '2rem',   // 32px
    '4xl': '2.5rem', // 40px
};

export const fontWeight = {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
};

export const shadows = {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
    xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
    glow: (color: string) => `0 0 20px ${color}`,
    innerGlow: (color: string) => `inset 0 0 20px ${color}`,
};

export const transitions = {
    fast: '150ms ease',
    normal: '200ms ease',
    slow: '300ms ease',
    bounce: '300ms cubic-bezier(0.68, -0.55, 0.265, 1.55)',
};

// Card-related styles
export const cardStyles = {
    width: '70px',
    height: '100px',
    borderRadius: borderRadius.lg,
    background: 'linear-gradient(135deg, #ffffff 0%, #f0f0f0 100%)',
    shadow: shadows.lg,
};

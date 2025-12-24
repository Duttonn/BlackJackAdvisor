// Rainbet-Exact Design Tokens
// Deep Navy/Midnight Aesthetic

export const colors = {
    // Core Background Colors
    bg: '#0f1328',
    header: '#191F3B',
    sidebar: '#1B213C',
    surface: '#252B46',
    surfaceHover: '#2d3452',
    surfaceActive: '#353d5e',

    // Borders
    border: 'rgba(255, 255, 255, 0.05)',
    borderLight: 'rgba(255, 255, 255, 0.1)',

    // Primary Blue
    primary: '#0077DB',
    primaryHover: '#0066c2',
    primaryLight: '#3399e6',

    // Success Green
    green: '#39F26E',
    greenHover: '#2dd85d',
    greenGlow: 'rgba(57, 242, 110, 0.2)',

    // Danger Red
    red: '#FF4757',
    redHover: '#e6404f',
    redGlow: 'rgba(255, 71, 87, 0.2)',

    // Warning Amber
    amber: '#FFB347',
    amberHover: '#e6a13f',

    // Text Colors
    text: '#FFFFFF',
    textSecondary: '#B8BDD9',
    textMuted: '#7C83B1',
    textDim: '#545B7E',

    // Card Suit Colors
    cardRed: '#dc2626',
    cardBlack: '#1f2937',
};

export const layout = {
    headerHeight: '68px',
    sidebarWidth: '250px',
};

export const shadows = {
    default: '0 4px 20px rgba(0, 0, 0, 0.3)',
    lg: '0 8px 40px rgba(0, 0, 0, 0.4)',
    glow: (color: string) => `0 0 20px ${color}`,
};

export const borderRadius = {
    sm: '6px',
    md: '8px',
    lg: '12px',
    xl: '16px',
    full: '9999px',
};

export const transitions = {
    fast: '150ms ease',
    normal: '200ms ease',
    slow: '300ms ease',
};

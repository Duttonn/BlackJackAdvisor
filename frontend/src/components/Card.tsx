// Playing card component

interface CardProps {
    card: string;
    size?: 'sm' | 'md' | 'lg';
    faceDown?: boolean;
    className?: string;
    animate?: boolean;
}

/**
 * Playing card display component
 * Handles card notation like "A♥", "K♦", "T♣", "5♠"
 */
export function Card({
    card,
    size = 'md',
    faceDown = false,
    className = '',
    animate = false,
}: CardProps) {
    // Parse card string
    const parseCard = (
        cardStr: string
    ): { rank: string; suit: string; isRed: boolean } => {
        if (!cardStr || cardStr.length < 2) {
            return { rank: '?', suit: '?', isRed: false };
        }

        const rank = cardStr.charAt(0).toUpperCase();
        const suitChar = cardStr.charAt(1).toLowerCase();

        let suit: string;
        let isRed: boolean;

        switch (suitChar) {
            case 'h':
            case '♥':
                suit = '♥';
                isRed = true;
                break;
            case 'd':
            case '♦':
                suit = '♦';
                isRed = true;
                break;
            case 'c':
            case '♣':
                suit = '♣';
                isRed = false;
                break;
            case 's':
            case '♠':
                suit = '♠';
                isRed = false;
                break;
            default:
                suit = suitChar;
                isRed = false;
        }

        const displayRank = rank === 'T' ? '10' : rank;
        return { rank: displayRank, suit, isRed };
    };

    const { rank, suit, isRed } = parseCard(card);

    // Size configs
    const sizes = {
        sm: { w: 'w-12', h: 'h-[68px]', text: 'text-xs', center: 'text-xl', p: 'p-1' },
        md: { w: 'w-[70px]', h: 'h-[98px]', text: 'text-sm', center: 'text-2xl', p: 'p-1.5' },
        lg: { w: 'w-[80px]', h: 'h-[112px]', text: 'text-base', center: 'text-3xl', p: 'p-2' },
    };

    const s = sizes[size];

    if (faceDown) {
        return (
            <div
                className={`
          ${s.w} ${s.h}
          rounded-xl shadow-lg
          bg-gradient-to-br from-[#1a2555] to-[#0f1a45]
          border-2 border-white/10
          flex items-center justify-center
          transition-transform duration-200
          hover:translate-y-[-4px]
          ${animate ? 'animate-card-deal' : ''}
          ${className}
        `}
            >
                <div className="text-3xl text-[var(--rb-primary)]/30">♠</div>
            </div>
        );
    }

    return (
        <div
            className={`
        ${s.w} ${s.h}
        rounded-xl shadow-lg
        bg-gradient-to-b from-white to-gray-100
        border border-gray-200
        flex flex-col justify-between
        transition-transform duration-200
        hover:translate-y-[-4px]
        relative overflow-hidden
        ${animate ? 'animate-card-deal' : ''}
        ${className}
      `}
        >
            {/* Top left */}
            <div className={`${s.p} leading-none ${isRed ? 'text-red-500' : 'text-gray-900'}`}>
                <div className={`${s.text} font-bold`}>{rank}</div>
                <div className={`${s.text}`}>{suit}</div>
            </div>

            {/* Center suit */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <span className={`${s.center} ${isRed ? 'text-red-500' : 'text-gray-900'}`}>
                    {suit}
                </span>
            </div>

            {/* Bottom right (rotated) */}
            <div
                className={`${s.p} leading-none ${isRed ? 'text-red-500' : 'text-gray-900'} self-end rotate-180`}
            >
                <div className={`${s.text} font-bold`}>{rank}</div>
                <div className={`${s.text}`}>{suit}</div>
            </div>
        </div>
    );
}

// Card stack for multiple cards with overlap
interface CardStackProps {
    cards: string[];
    size?: 'sm' | 'md' | 'lg';
    overlap?: number;
    className?: string;
}

export function CardStack({
    cards,
    size = 'md',
    overlap = 30,
    className = '',
}: CardStackProps) {
    if (cards.length === 0) {
        return (
            <div className={`flex items-center justify-center text-[var(--rb-text-dim)] ${className}`}>
                No cards
            </div>
        );
    }

    return (
        <div className={`flex ${className}`}>
            {cards.map((card, index) => (
                <div
                    key={`${card}-${index}`}
                    style={{ marginLeft: index === 0 ? 0 : -overlap }}
                    className="transition-all duration-200 hover:z-10"
                >
                    <Card card={card} size={size} animate={index === cards.length - 1} />
                </div>
            ))}
        </div>
    );
}

export default Card;

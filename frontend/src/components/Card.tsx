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
    // Parse card string - format is like "A♥" or "Ah" or "A♥"
    const parseCard = (cardStr: string): { rank: string; suit: string; isRed: boolean } => {
        if (!cardStr || cardStr.length < 2) {
            return { rank: '?', suit: '?', isRed: false };
        }

        const rank = cardStr.charAt(0).toUpperCase();
        const suitChar = cardStr.charAt(1).toLowerCase();

        // Convert suit notation
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

        // Convert T to 10 for display
        const displayRank = rank === 'T' ? '10' : rank;

        return { rank: displayRank, suit, isRed };
    };

    const { rank, suit, isRed } = parseCard(card);

    // Size classes
    const sizeStyles = {
        sm: {
            width: 'w-12',
            height: 'h-[68px]',
            fontSize: 'text-sm',
            padding: 'p-1',
        },
        md: {
            width: 'w-[70px]',
            height: 'h-[100px]',
            fontSize: 'text-lg',
            padding: 'p-2',
        },
        lg: {
            width: 'w-[90px]',
            height: 'h-[130px]',
            fontSize: 'text-2xl',
            padding: 'p-3',
        },
    };

    const currentSize = sizeStyles[size];

    if (faceDown) {
        return (
            <div
                className={`
          ${currentSize.width} ${currentSize.height}
          rounded-lg shadow-lg
          bg-gradient-to-br from-blue-800 to-blue-900
          border-2 border-blue-700
          flex items-center justify-center
          transition-transform duration-200
          hover:translate-y-[-4px] hover:shadow-xl
          ${animate ? 'card-flip' : ''}
          ${className}
        `}
            >
                <div className="text-blue-400 text-4xl opacity-30">✦</div>
            </div>
        );
    }

    return (
        <div
            className={`
        ${currentSize.width} ${currentSize.height}
        rounded-lg shadow-lg
        bg-gradient-to-br from-white to-gray-100
        border border-gray-300
        flex flex-col
        transition-transform duration-200
        hover:translate-y-[-4px] hover:shadow-xl
        relative overflow-hidden
        ${animate ? 'card-flip' : ''}
        ${className}
      `}
        >
            {/* Top-left rank and suit */}
            <div
                className={`
          ${currentSize.padding}
          font-bold leading-none
          ${isRed ? 'text-red-500' : 'text-gray-900'}
        `}
            >
                <div className={currentSize.fontSize}>{rank}</div>
                <div className={currentSize.fontSize}>{suit}</div>
            </div>

            {/* Center suit */}
            <div className="flex-1 flex items-center justify-center">
                <span
                    className={`
            ${size === 'lg' ? 'text-5xl' : size === 'md' ? 'text-3xl' : 'text-2xl'}
            ${isRed ? 'text-red-500' : 'text-gray-900'}
          `}
                >
                    {suit}
                </span>
            </div>

            {/* Bottom-right rank and suit (inverted) */}
            <div
                className={`
          ${currentSize.padding}
          font-bold leading-none
          ${isRed ? 'text-red-500' : 'text-gray-900'}
          self-end rotate-180
        `}
            >
                <div className={currentSize.fontSize}>{rank}</div>
                <div className={currentSize.fontSize}>{suit}</div>
            </div>
        </div>
    );
}

// Card stack for displaying multiple cards with overlap
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
            <div className={`flex items-center justify-center text-gray-500 ${className}`}>
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
                    <Card
                        card={card}
                        size={size}
                        animate={index === cards.length - 1}
                    />
                </div>
            ))}
        </div>
    );
}

export default Card;

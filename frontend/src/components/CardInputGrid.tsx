/**
 * CardInputGrid.tsx
 * 
 * "Hold-to-Reveal" 5-Direction Radial Card Input
 * 
 * Three clean buttons (LOW/MID/HIGH) that reveal a radial menu on press:
 * - LOW (+1): 2,3,4,5,6 - Green (5 directions)
 * - MID (0): 7,8,9 - Gray (3 directions: up/center/down)
 * - HIGH (-1): T,J,Q,K,A - Red (5 directions)
 * 
 * Press and drag toward a direction to select specific rank,
 * or tap center to select the default rank.
 */

import { useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// Default suit (suits don't matter for Hi-Lo counting)
const DEFAULT_SUIT = '♠';

// 5-direction type
type Direction = 'TOP' | 'BOTTOM' | 'LEFT' | 'RIGHT' | 'CENTER';

// Card zones configuration with 5 directions
const ZONES = {
    LOW: {
        label: 'LOW',
        value: '+1',
        bgClass: 'bg-emerald-600',
        hoverClass: 'hover:bg-emerald-500',
        activeClass: 'bg-emerald-700',
        bubbleBg: 'bg-emerald-500',
        bubbleBorder: 'border-emerald-300',
        // 5 directions for 5 low cards
        cards: {
            TOP: '6',
            RIGHT: '5',
            CENTER: '4',
            LEFT: '3',
            BOTTOM: '2',
        } as Record<Direction, string>,
        defaultRank: '4',
    },
    MID: {
        label: 'MID',
        value: '0',
        bgClass: 'bg-slate-600',
        hoverClass: 'hover:bg-slate-500',
        activeClass: 'bg-slate-700',
        bubbleBg: 'bg-slate-500',
        bubbleBorder: 'border-slate-300',
        // 3 directions for 3 neutral cards (no left/right)
        cards: {
            TOP: '9',
            CENTER: '8',
            BOTTOM: '7',
        } as Record<Direction, string>,
        defaultRank: '8',
    },
    HIGH: {
        label: 'HIGH',
        value: '-1',
        bgClass: 'bg-rose-600',
        hoverClass: 'hover:bg-rose-500',
        activeClass: 'bg-rose-700',
        bubbleBg: 'bg-rose-500',
        bubbleBorder: 'border-rose-300',
        // 5 directions for 5 high cards
        cards: {
            TOP: 'A',
            RIGHT: 'K',
            CENTER: 'Q',
            LEFT: 'J',
            BOTTOM: 'T',
        } as Record<Direction, string>,
        defaultRank: 'Q',
    },
} as const;

type ZoneKey = keyof typeof ZONES;

export interface CardInputGridProps {
    onCardSelect: (card: string) => void;
    prompt?: string;
    disabled?: boolean;
    showModeToggle?: boolean;
    defaultMode?: 'speed' | 'classic';
}

export function CardInputGrid({
    onCardSelect,
    prompt,
    disabled = false,
}: CardInputGridProps) {
    // Active zone being pressed
    const [activeZone, setActiveZone] = useState<ZoneKey | null>(null);
    // Current drag direction
    const [dragDirection, setDragDirection] = useState<Direction>('CENTER');
    // Last selected card (for feedback)
    const [lastCard, setLastCard] = useState<string | null>(null);
    // Animation trigger
    const [showFeedback, setShowFeedback] = useState(false);

    // Touch/pointer start position
    const startPos = useRef<{ x: number; y: number } | null>(null);
    const DRAG_THRESHOLD = 25; // pixels to consider a drag

    // Calculate 5-direction from drag
    const calculateDirection = useCallback((clientX: number, clientY: number): Direction => {
        if (!startPos.current) return 'CENTER';

        const dx = clientX - startPos.current.x;
        const dy = clientY - startPos.current.y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance < DRAG_THRESHOLD) {
            return 'CENTER';
        }

        // Determine primary direction based on angle
        const absX = Math.abs(dx);
        const absY = Math.abs(dy);

        if (absY > absX) {
            // Vertical movement dominant
            return dy < 0 ? 'TOP' : 'BOTTOM';
        } else {
            // Horizontal movement dominant
            return dx > 0 ? 'RIGHT' : 'LEFT';
        }
    }, []);

    // Handle pointer down - start holding
    const handlePointerDown = useCallback((zone: ZoneKey, e: React.PointerEvent) => {
        if (disabled) return;
        e.preventDefault();
        (e.target as HTMLElement).setPointerCapture(e.pointerId);

        setActiveZone(zone);
        setDragDirection('CENTER');
        startPos.current = { x: e.clientX, y: e.clientY };
    }, [disabled]);

    // Handle pointer move - update direction
    const handlePointerMove = useCallback((e: React.PointerEvent) => {
        if (!activeZone || !startPos.current) return;

        const direction = calculateDirection(e.clientX, e.clientY);
        setDragDirection(direction);
    }, [activeZone, calculateDirection]);

    // Handle pointer up - select card
    const handlePointerUp = useCallback((e: React.PointerEvent) => {
        if (!activeZone) return;
        (e.target as HTMLElement).releasePointerCapture(e.pointerId);

        const zone = ZONES[activeZone];
        const cards = zone.cards;

        // Get the card for this direction, fallback to center if direction doesn't exist
        let rank = cards[dragDirection];
        if (!rank) {
            rank = cards.CENTER;
        }

        const card = `${rank}${DEFAULT_SUIT}`;

        // Feedback
        setLastCard(card);
        setShowFeedback(true);
        setTimeout(() => setShowFeedback(false), 600);

        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate(10);
        }

        // Send to parent
        onCardSelect(card);

        // Reset
        setActiveZone(null);
        setDragDirection('CENTER');
        startPos.current = null;
    }, [activeZone, dragDirection, onCardSelect]);

    // Handle pointer cancel
    const handlePointerCancel = useCallback(() => {
        setActiveZone(null);
        setDragDirection('CENTER');
        startPos.current = null;
    }, []);

    // Render 5-direction radial bubbles
    const renderRadialMenu = (zoneKey: ZoneKey) => {
        const zone = ZONES[zoneKey];
        const isActive = activeZone === zoneKey;

        if (!isActive) return null;

        const hasLeftRight = zoneKey !== 'MID'; // MID only has 3 cards

        const bubbleBase = `
            flex items-center justify-center font-bold text-white
            border-2 shadow-lg transition-transform
            ${zone.bubbleBg} ${zone.bubbleBorder}
        `;

        return (
            <motion.div
                className="absolute inset-0 pointer-events-none"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
            >
                {/* TOP */}
                <motion.div
                    initial={{ scale: 0, y: 20 }}
                    animate={{
                        scale: dragDirection === 'TOP' ? 1.3 : 1,
                        y: 0
                    }}
                    className={`
                        absolute top-2 left-1/2 -translate-x-1/2
                        w-10 h-10 rounded-full text-lg
                        ${bubbleBase}
                        ${dragDirection === 'TOP' ? 'ring-2 ring-white' : 'opacity-70'}
                    `}
                >
                    {zone.cards.TOP}
                </motion.div>

                {/* BOTTOM */}
                <motion.div
                    initial={{ scale: 0, y: -20 }}
                    animate={{
                        scale: dragDirection === 'BOTTOM' ? 1.3 : 1,
                        y: 0
                    }}
                    className={`
                        absolute bottom-2 left-1/2 -translate-x-1/2
                        w-10 h-10 rounded-full text-lg
                        ${bubbleBase}
                        ${dragDirection === 'BOTTOM' ? 'ring-2 ring-white' : 'opacity-70'}
                    `}
                >
                    {zone.cards.BOTTOM}
                </motion.div>

                {/* LEFT (only for LOW and HIGH) */}
                {hasLeftRight && (
                    <motion.div
                        initial={{ scale: 0, x: 20 }}
                        animate={{
                            scale: dragDirection === 'LEFT' ? 1.3 : 1,
                            x: 0
                        }}
                        className={`
                            absolute left-2 top-1/2 -translate-y-1/2
                            w-10 h-10 rounded-full text-lg
                            ${bubbleBase}
                            ${dragDirection === 'LEFT' ? 'ring-2 ring-white' : 'opacity-70'}
                        `}
                    >
                        {zone.cards.LEFT}
                    </motion.div>
                )}

                {/* RIGHT (only for LOW and HIGH) */}
                {hasLeftRight && (
                    <motion.div
                        initial={{ scale: 0, x: -20 }}
                        animate={{
                            scale: dragDirection === 'RIGHT' ? 1.3 : 1,
                            x: 0
                        }}
                        className={`
                            absolute right-2 top-1/2 -translate-y-1/2
                            w-10 h-10 rounded-full text-lg
                            ${bubbleBase}
                            ${dragDirection === 'RIGHT' ? 'ring-2 ring-white' : 'opacity-70'}
                        `}
                    >
                        {zone.cards.RIGHT}
                    </motion.div>
                )}

                {/* CENTER */}
                <motion.div
                    initial={{ scale: 0 }}
                    animate={{
                        scale: dragDirection === 'CENTER' ? 1.4 : 1
                    }}
                    className={`
                        absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2
                        w-14 h-14 rounded-full text-xl
                        ${bubbleBase}
                        ${dragDirection === 'CENTER' ? 'ring-2 ring-white' : 'opacity-70'}
                    `}
                >
                    {zone.cards.CENTER}
                </motion.div>
            </motion.div>
        );
    };

    return (
        <div className="space-y-3">
            {/* Prompt */}
            {prompt && (
                <div className="text-center text-sm font-medium text-slate-400">
                    {prompt}
                </div>
            )}

            {/* Last Card Feedback */}
            <AnimatePresence>
                {showFeedback && lastCard && (
                    <motion.div
                        initial={{ opacity: 0, y: 10, scale: 0.8 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.8 }}
                        className="flex items-center justify-center py-2"
                    >
                        <span className="px-4 py-2 rounded-full bg-slate-700 text-white font-bold text-xl shadow-lg">
                            {lastCard}
                        </span>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Three Zone Buttons */}
            <div
                className="grid grid-cols-3 gap-3"
                onPointerMove={handlePointerMove}
                onPointerUp={handlePointerUp}
                onPointerCancel={handlePointerCancel}
            >
                {(Object.keys(ZONES) as ZoneKey[]).map((zoneKey) => {
                    const zone = ZONES[zoneKey];
                    const isActive = activeZone === zoneKey;

                    return (
                        <motion.button
                            key={zoneKey}
                            onPointerDown={(e) => handlePointerDown(zoneKey, e)}
                            disabled={disabled}
                            className={`
                                relative h-36 rounded-2xl font-bold
                                touch-none select-none cursor-pointer
                                transition-all duration-150
                                ${zone.bgClass}
                                ${isActive ? zone.activeClass : zone.hoverClass}
                                ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
                                shadow-lg text-white
                            `}
                            whileTap={{ scale: 0.98 }}
                        >
                            {/* Default Label (hidden when active) */}
                            <AnimatePresence>
                                {!isActive && (
                                    <motion.div
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0, scale: 0.8 }}
                                        className="absolute inset-0 flex flex-col items-center justify-center"
                                    >
                                        <span className="text-3xl font-black">{zone.label}</span>
                                        <span className="text-lg opacity-70">{zone.value}</span>
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            {/* Radial Menu (shown when active) */}
                            <AnimatePresence>
                                {renderRadialMenu(zoneKey)}
                            </AnimatePresence>
                        </motion.button>
                    );
                })}
            </div>

            {/* Legend */}
            <div className="grid grid-cols-3 gap-2 text-[10px] text-slate-500 text-center">
                <div>
                    <span className="text-emerald-400">↑6</span> ·
                    <span className="text-emerald-400">→5</span> ·
                    <span className="text-emerald-400">●4</span> ·
                    <span className="text-emerald-400">←3</span> ·
                    <span className="text-emerald-400">↓2</span>
                </div>
                <div>
                    <span className="text-slate-400">↑9</span> ·
                    <span className="text-slate-400">●8</span> ·
                    <span className="text-slate-400">↓7</span>
                </div>
                <div>
                    <span className="text-rose-400">↑A</span> ·
                    <span className="text-rose-400">→K</span> ·
                    <span className="text-rose-400">●Q</span> ·
                    <span className="text-rose-400">←J</span> ·
                    <span className="text-rose-400">↓T</span>
                </div>
            </div>
        </div>
    );
}

export default CardInputGrid;

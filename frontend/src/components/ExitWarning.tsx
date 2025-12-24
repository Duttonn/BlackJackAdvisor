import { useEffect } from 'react';
import { AlertTriangle, DoorOpen, X } from 'lucide-react';

interface ExitWarningProps {
    reason: string;
    onDismiss?: () => void;
    onExitTable?: () => void;
    className?: string;
}

/**
 * Wong Out exit warning component
 * Displays a prominent alert when the count suggests leaving the table
 */
export function ExitWarning({
    reason,
    onDismiss,
    onExitTable,
    className = '',
}: ExitWarningProps) {
    return (
        <div
            className={`
        relative overflow-hidden
        bg-gradient-to-r from-red-900/90 to-red-800/90
        border-2 border-red-500
        rounded-xl p-6
        exit-warning
        ${className}
      `}
        >
            {/* Background glow effect */}
            <div className="absolute inset-0 bg-red-500/10 animate-pulse pointer-events-none" />

            {/* Content */}
            <div className="relative z-10">
                <div className="flex items-start gap-4">
                    {/* Warning icon */}
                    <div className="flex-shrink-0 p-3 bg-red-500/20 rounded-full">
                        <AlertTriangle className="w-8 h-8 text-red-400 animate-pulse" />
                    </div>

                    {/* Message */}
                    <div className="flex-1">
                        <h3 className="text-xl font-bold text-red-300 mb-2 flex items-center gap-2">
                            <DoorOpen className="w-5 h-5" />
                            Wong Out Signal
                        </h3>
                        <p className="text-red-200 mb-4">
                            {reason}
                        </p>
                        <p className="text-sm text-red-300/80">
                            The count has dropped below the threshold. Consider leaving the table to preserve your bankroll.
                        </p>
                    </div>

                    {/* Dismiss button */}
                    {onDismiss && (
                        <button
                            onClick={onDismiss}
                            className="flex-shrink-0 p-2 text-red-400 hover:text-red-300 hover:bg-red-500/20 rounded-lg transition-colors"
                            aria-label="Dismiss warning"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    )}
                </div>

                {/* Action buttons */}
                <div className="flex gap-3 mt-4 pt-4 border-t border-red-500/30">
                    {onExitTable && (
                        <button
                            onClick={onExitTable}
                            className="
                flex items-center gap-2 px-4 py-2
                bg-red-500 hover:bg-red-400
                text-white font-semibold
                rounded-lg transition-colors
              "
                        >
                            <DoorOpen className="w-4 h-4" />
                            Leave Table
                        </button>
                    )}
                    {onDismiss && (
                        <button
                            onClick={onDismiss}
                            className="
                flex items-center gap-2 px-4 py-2
                bg-red-500/20 hover:bg-red-500/30
                text-red-300 font-semibold
                rounded-lg transition-colors
              "
                        >
                            Continue Playing
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}

// Compact inline warning
interface InlineWarningProps {
    reason: string;
    className?: string;
}

export function InlineExitWarning({
    reason,
    className = '',
}: InlineWarningProps) {
    return (
        <div
            className={`
        flex items-center gap-2 px-4 py-2
        bg-red-500/20 border border-red-500/50
        rounded-lg text-sm text-red-300
        ${className}
      `}
        >
            <AlertTriangle className="w-4 h-4 flex-shrink-0 animate-pulse" />
            <span className="font-medium">{reason}</span>
        </div>
    );
}

// Toast-style notification
interface ExitToastProps {
    reason: string;
    onClose: () => void;
    autoClose?: number; // Auto close after ms
    className?: string;
}

export function ExitToast({
    reason,
    onClose,
    autoClose,
    className = '',
}: ExitToastProps) {
    useEffect(() => {
        if (autoClose) {
            const timer = setTimeout(onClose, autoClose);
            return () => clearTimeout(timer);
        }
    }, [autoClose, onClose]);

    return (
        <div
            className={`
        fixed bottom-6 right-6 z-50
        bg-red-900/95 border border-red-500
        rounded-xl shadow-2xl
        p-4 max-w-md
        slide-in-right exit-warning
        ${className}
      `}
        >
            <div className="flex items-start gap-3">
                <AlertTriangle className="w-6 h-6 text-red-400 flex-shrink-0" />
                <div className="flex-1">
                    <h4 className="font-bold text-red-300 mb-1">Wong Out Signal</h4>
                    <p className="text-sm text-red-200">{reason}</p>
                </div>
                <button
                    onClick={onClose}
                    className="text-red-400 hover:text-red-300"
                >
                    <X className="w-5 h-5" />
                </button>
            </div>
        </div>
    );
}

export default ExitWarning;

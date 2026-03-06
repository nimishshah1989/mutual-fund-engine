interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export default function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-10 text-center">
      <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-4">
        <svg
          className="w-6 h-6 text-red-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
          />
        </svg>
      </div>
      <p className="text-sm font-medium text-slate-800">Something went wrong</p>
      <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          aria-label="Retry the failed operation"
          className="mt-4 bg-teal-600 text-white font-medium px-4 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm"
        >
          Try Again
        </button>
      )}
    </div>
  );
}

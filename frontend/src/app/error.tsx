"use client";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="bg-white border border-red-200 rounded-lg p-8 max-w-md shadow-sm">
        <h2 className="text-lg font-semibold text-red-700 mb-2">
          Something went wrong
        </h2>
        <p className="text-sm text-slate-500 mb-4">
          {error.message || "An unexpected error occurred."}
        </p>
        <button
          onClick={reset}
          aria-label="Retry after error"
          className="px-4 py-2 text-sm font-medium text-white bg-teal-600 rounded-md hover:bg-teal-700 transition-colors"
        >
          Try again
        </button>
      </div>
    </div>
  );
}

interface LoadingSkeletonProps {
  /** Number of skeleton rows to render (default: 1) */
  rows?: number;
  /** Height of each row in Tailwind class form (default: "h-4") */
  height?: string;
  /** Optional width override (default: "w-full") */
  width?: string;
  /** Render as a grid of stat cards */
  variant?: "text" | "card" | "table";
  /** Number of stat cards in a card variant (default: 6) */
  cardCount?: number;
}

export default function LoadingSkeleton({
  rows = 1,
  height = "h-4",
  width = "w-full",
  variant = "text",
  cardCount = 6,
}: LoadingSkeletonProps) {
  if (variant === "card") {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
        {Array.from({ length: cardCount }).map((_, i) => (
          <div
            key={i}
            className="bg-white rounded-xl border border-slate-200 p-5"
          >
            <div className="h-3 w-20 bg-slate-100 animate-pulse rounded" />
            <div className="h-7 w-28 bg-slate-100 animate-pulse rounded mt-2" />
            <div className="h-3 w-16 bg-slate-100 animate-pulse rounded mt-2" />
          </div>
        ))}
      </div>
    );
  }

  if (variant === "table") {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        {/* Table header skeleton */}
        <div className="flex gap-4 mb-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-3 bg-slate-100 animate-pulse rounded flex-1"
            />
          ))}
        </div>
        {/* Table rows */}
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="flex gap-4 py-3 border-b border-slate-100">
            {Array.from({ length: 6 }).map((_, j) => (
              <div
                key={j}
                className="h-4 bg-slate-100 animate-pulse rounded flex-1"
              />
            ))}
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className={`${height} ${width} bg-slate-100 animate-pulse rounded`}
        />
      ))}
    </div>
  );
}

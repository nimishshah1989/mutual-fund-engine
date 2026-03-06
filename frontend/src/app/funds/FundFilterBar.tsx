"use client";

/* ------------------------------------------------------------------ */
/*  Fund Filter Bar -- search, category, action filter controls        */
/* ------------------------------------------------------------------ */

interface FundFilterBarProps {
  search: string;
  onSearchChange: (value: string) => void;
  categoryFilter: string;
  onCategoryChange: (value: string) => void;
  actionFilter: string;
  onActionChange: (value: string) => void;
  categories: string[];
  displayCount: number;
  totalCount: number;
  matrixSelected?: boolean;
  onClearMatrix?: () => void;
}

const ACTION_OPTIONS = [
  "ACCUMULATE",
  "HOLD",
  "REDUCE",
  "EXIT",
] as const;

const ACTION_LABELS: Record<string, string> = {
  ACCUMULATE: "ACCUMULATE",
  HOLD: "HOLD",
  REDUCE: "REDUCE",
  EXIT: "EXIT",
};

const selectClasses =
  "bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none";

export default function FundFilterBar({
  search,
  onSearchChange,
  categoryFilter,
  onCategoryChange,
  actionFilter,
  onActionChange,
  categories,
  displayCount,
  totalCount,
  matrixSelected = false,
  onClearMatrix,
}: FundFilterBarProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 mb-4">
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="text"
          placeholder="Search by fund name..."
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          aria-label="Search funds by name"
          className="w-64 bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
        />

        <select
          value={categoryFilter}
          onChange={(e) => onCategoryChange(e.target.value)}
          aria-label="Filter by category"
          className={selectClasses}
        >
          <option value="">All Categories</option>
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat}
            </option>
          ))}
        </select>

        <select
          value={actionFilter}
          onChange={(e) => onActionChange(e.target.value)}
          aria-label="Filter by action"
          className={selectClasses}
        >
          <option value="">All Actions</option>
          {ACTION_OPTIONS.map((action) => (
            <option key={action} value={action}>
              {ACTION_LABELS[action]}
            </option>
          ))}
        </select>

        {matrixSelected && onClearMatrix && (
          <button
            onClick={onClearMatrix}
            className="bg-white text-slate-600 font-medium px-3 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors text-sm flex items-center gap-1.5"
            aria-label="Clear matrix cell selection"
          >
            <svg
              className="w-3.5 h-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
            Clear matrix selection
          </button>
        )}

        <div className="ml-auto text-sm text-slate-500">
          Showing{" "}
          <span className="font-semibold text-slate-700">{displayCount}</span>{" "}
          of <span className="font-semibold text-slate-700">{totalCount}</span>{" "}
          funds
        </div>
      </div>
    </div>
  );
}

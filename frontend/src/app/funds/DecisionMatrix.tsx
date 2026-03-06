"use client";

import type { MatrixCellSummary } from "@/types/api-scores";
import { formatScore } from "@/lib/formatters";

/* ------------------------------------------------------------------ */
/*  Decision Matrix — 3x3 visual grid (QFS rows x FMS columns)        */
/*                                                                     */
/*  Layout (rows = QFS top-to-bottom, cols = FMS left-to-right):       */
/*                    LOW (FMS)       MID (FMS)       HIGH (FMS)       */
/*  HIGH (QFS):      HIGH_LOW        HIGH_MID        HIGH_HIGH         */
/*  MID  (QFS):      MID_LOW         MID_MID         MID_HIGH          */
/*  LOW  (QFS):      LOW_LOW         LOW_MID         LOW_HIGH          */
/* ------------------------------------------------------------------ */

interface DecisionMatrixProps {
  cells: MatrixCellSummary[];
  selectedPosition: string | null;
  onCellClick: (position: string | null) => void;
}

const ROW_LABELS = ["HIGH", "MID", "LOW"] as const;
const COL_LABELS = ["LOW", "MID", "HIGH"] as const;

/* ---- Action-based cell styling ---- */
interface CellStyle {
  bg: string;
  border: string;
  text: string;
  activeBorder: string;
}

const ACTION_CELL_STYLES: Record<string, CellStyle> = {
  ACCUMULATE: {
    bg: "bg-emerald-50",
    border: "border-emerald-300",
    text: "text-emerald-700",
    activeBorder: "border-emerald-500 ring-2 ring-emerald-200",
  },
  HOLD: {
    bg: "bg-amber-50",
    border: "border-amber-300",
    text: "text-amber-700",
    activeBorder: "border-amber-500 ring-2 ring-amber-200",
  },
  REDUCE: {
    bg: "bg-orange-50",
    border: "border-orange-300",
    text: "text-orange-700",
    activeBorder: "border-orange-500 ring-2 ring-orange-200",
  },
  EXIT: {
    bg: "bg-red-50",
    border: "border-red-300",
    text: "text-red-700",
    activeBorder: "border-red-500 ring-2 ring-red-200",
  },
};

const FALLBACK_STYLE: CellStyle = {
  bg: "bg-slate-50",
  border: "border-slate-300",
  text: "text-slate-600",
  activeBorder: "border-slate-500 ring-2 ring-slate-200",
};

function getCellStyle(action: string): CellStyle {
  return ACTION_CELL_STYLES[action.toUpperCase()] ?? FALLBACK_STYLE;
}

/* ---- Star position for the ACCUMULATE + HIGH_HIGH cell ---- */
const STAR_POSITION = "HIGH_HIGH";

export default function DecisionMatrix({
  cells,
  selectedPosition,
  onCellClick,
}: DecisionMatrixProps) {
  /* Build a lookup map: position -> cell data */
  const cellMap = new Map<string, MatrixCellSummary>();
  for (const cell of cells) {
    cellMap.set(cell.matrix_position, cell);
  }

  function handleCellClick(position: string) {
    if (selectedPosition === position) {
      onCellClick(null);
    } else {
      onCellClick(position);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="text-base font-semibold text-slate-800 mb-4">
        Decision Matrix
      </h3>

      <div className="overflow-x-auto">
        {/* Grid container with row labels and column labels */}
        <div className="inline-block min-w-[340px]">
          {/* Column headers (FMS axis) */}
          <div className="grid grid-cols-[48px_1fr_1fr_1fr] gap-1.5 mb-1.5">
            {/* Empty corner cell */}
            <div />
            {COL_LABELS.map((label) => (
              <div
                key={`col-${label}`}
                className="text-center text-xs font-semibold text-slate-400 uppercase tracking-wider py-1"
              >
                <span className="hidden sm:inline">FMS: </span>
                {label}
              </div>
            ))}
          </div>

          {/* Matrix rows */}
          {ROW_LABELS.map((rowLabel) => (
            <div
              key={`row-${rowLabel}`}
              className="grid grid-cols-[48px_1fr_1fr_1fr] gap-1.5 mb-1.5"
            >
              {/* Row label (QFS axis) */}
              <div className="flex items-center justify-center">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider [writing-mode:vertical-lr] rotate-180">
                  <span className="hidden sm:inline">QFS: </span>
                  {rowLabel}
                </span>
              </div>

              {/* 3 cells for this row */}
              {COL_LABELS.map((colLabel) => {
                const position = `${rowLabel}_${colLabel}`;
                const cell = cellMap.get(position);
                const isSelected = selectedPosition === position;
                const action = cell?.action?.toUpperCase() ?? "";
                const style = action ? getCellStyle(action) : FALLBACK_STYLE;
                const isStarCell = position === STAR_POSITION;

                return (
                  <button
                    key={position}
                    type="button"
                    onClick={() => handleCellClick(position)}
                    className={[
                      "relative rounded-lg p-3 sm:p-4 transition-all cursor-pointer text-left",
                      style.bg,
                      isSelected
                        ? `border-2 ${style.activeBorder}`
                        : `border ${style.border}`,
                      "hover:shadow-sm",
                    ].join(" ")}
                    aria-label={`Matrix cell ${rowLabel} QFS, ${colLabel} FMS${cell ? ` - ${cell.action} - ${cell.fund_count} funds` : " - empty"}`}
                  >
                    {/* Star marker for HIGH_HIGH */}
                    {isStarCell && (
                      <span className="absolute top-1 right-1.5 text-xs text-amber-500 font-bold">
                        &#9733;
                      </span>
                    )}

                    {cell ? (
                      <>
                        {/* Action label */}
                        <p
                          className={`text-xs sm:text-sm font-bold uppercase ${style.text} leading-tight`}
                        >
                          {cell.action}
                          {isStarCell && (
                            <span className="ml-1 text-[10px] font-semibold text-amber-500">
                              STAR
                            </span>
                          )}
                        </p>

                        {/* Fund count */}
                        <p className="text-lg sm:text-xl font-bold font-mono tabular-nums text-slate-800 mt-1">
                          {cell.fund_count}
                        </p>

                        {/* Average scores */}
                        <div className="mt-1 space-y-0.5">
                          <p className="text-[10px] sm:text-xs text-slate-500">
                            <span className="text-slate-400">QFS </span>
                            <span className="font-mono tabular-nums font-medium text-slate-600">
                              {formatScore(cell.avg_qfs)}
                            </span>
                          </p>
                          <p className="text-[10px] sm:text-xs text-slate-500">
                            <span className="text-slate-400">FMS </span>
                            <span className="font-mono tabular-nums font-medium text-slate-600">
                              {formatScore(cell.avg_fms)}
                            </span>
                          </p>
                        </div>
                      </>
                    ) : (
                      /* Empty cell -- position exists but no funds scored into it */
                      <div className="text-center py-2">
                        <p className="text-xs text-slate-400">--</p>
                        <p className="text-lg font-bold font-mono tabular-nums text-slate-300 mt-1">
                          0
                        </p>
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          ))}

          {/* Horizontal axis label */}
          <div className="grid grid-cols-[48px_1fr] gap-1.5 mt-3">
            <div />
            <div className="flex items-center justify-between">
              <p className="text-[10px] sm:text-xs text-slate-400 italic">
                FM Signal Score (FMS) &rarr;
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Vertical axis label */}
      <div className="mt-2">
        <p className="text-[10px] sm:text-xs text-slate-400 italic">
          &uarr; Quantitative Fund Score (QFS)
        </p>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mt-4 pt-3 border-t border-slate-100">
        {Object.entries(ACTION_CELL_STYLES).map(([action, style]) => (
          <div key={action} className="flex items-center gap-1.5">
            <span
              className={`w-3 h-3 rounded ${style.bg} border ${style.border}`}
            />
            <span className={`text-xs font-medium ${style.text}`}>
              {action}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

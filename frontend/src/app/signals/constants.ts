/* ------------------------------------------------------------------ */
/*  Shared constants and types for the FM Sector Signals page          */
/* ------------------------------------------------------------------ */

export const SIGNAL_OPTIONS = [
  "OVERWEIGHT",
  "ACCUMULATE",
  "NEUTRAL",
  "UNDERWEIGHT",
  "AVOID",
] as const;

export const CONFIDENCE_OPTIONS = ["HIGH", "MEDIUM", "LOW"] as const;

export const CONFIDENCE_STYLES: Record<string, string> = {
  HIGH: "bg-emerald-100 text-emerald-700",
  MEDIUM: "bg-amber-100 text-amber-700",
  LOW: "bg-red-100 text-red-700",
};

export const UPDATED_BY_STORAGE_KEY = "jip_fm_signals_updated_by";

/** Per-row edit state for a single sector */
export interface SectorEditState {
  signal: string;
  confidence: string;
  notes: string;
}

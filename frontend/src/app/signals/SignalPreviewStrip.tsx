"use client";

/* ------------------------------------------------------------------ */
/*  Horizontal strip showing current signal per sector at a glance     */
/* ------------------------------------------------------------------ */

import SignalBadge from "@/components/SignalBadge";
import type { SectorWithSignal } from "@/types/api";
import type { SectorEditState } from "./constants";

interface SignalPreviewStripProps {
  sectors: SectorWithSignal[];
  edits: Record<string, SectorEditState>;
}

export default function SignalPreviewStrip({
  sectors,
  edits,
}: SignalPreviewStripProps) {
  if (sectors.length === 0) return null;

  return (
    <div className="mt-4 flex flex-wrap items-center gap-2">
      <span className="text-xs text-slate-400 font-medium mr-1">
        Current signals:
      </span>
      {sectors.map((sector) => {
        const currentSignal = edits[sector.sector_name]?.signal ?? "NEUTRAL";
        return (
          <div
            key={sector.sector_name}
            className="flex items-center gap-1.5"
          >
            <span className="text-xs text-slate-500">
              {sector.sector_name}
            </span>
            <SignalBadge signal={currentSignal} />
          </div>
        );
      })}
    </div>
  );
}

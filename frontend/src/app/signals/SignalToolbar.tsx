"use client";

/* ------------------------------------------------------------------ */
/*  Toolbar: Updated By input, change count, Save button, result toast */
/* ------------------------------------------------------------------ */

interface SaveResult {
  message: string;
  type: "success" | "error";
}

interface SignalToolbarProps {
  updatedBy: string;
  onUpdatedByChange: (value: string) => void;
  changedCount: number;
  hasChanges: boolean;
  canSave: boolean;
  saving: boolean;
  onSave: () => void;
  saveResult: SaveResult | null;
  onDismissResult: () => void;
}

export default function SignalToolbar({
  updatedBy,
  onUpdatedByChange,
  changedCount,
  hasChanges,
  canSave,
  saving,
  onSave,
  saveResult,
  onDismissResult,
}: SignalToolbarProps) {
  return (
    <>
      {/* Updated By + Save button bar */}
      <div className="flex items-end justify-between gap-4 mb-6">
        <div className="flex items-end gap-4">
          <div>
            <label className="text-xs text-slate-500 mb-1 block">
              Updated By <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={updatedBy}
              onChange={(e) => onUpdatedByChange(e.target.value)}
              placeholder="Your name (e.g. Nimish Shah)"
              aria-label="Updated by name"
              className="w-64 bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
            />
          </div>
          {hasChanges && (
            <p className="text-xs text-teal-600 font-medium pb-2">
              {changedCount} sector
              {changedCount !== 1 ? "s" : ""} modified
            </p>
          )}
        </div>
        <button
          onClick={onSave}
          disabled={!canSave}
          aria-label="Save all signal changes"
          className="bg-teal-600 text-white px-6 py-2.5 rounded-lg font-medium hover:bg-teal-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors text-sm"
        >
          {saving ? "Saving..." : "Save All Changes"}
        </button>
      </div>

      {/* Save result toast */}
      {saveResult && (
        <div
          className={`rounded-xl border p-4 mb-6 ${
            saveResult.type === "success"
              ? "bg-emerald-50 border-emerald-200"
              : "bg-red-50 border-red-200"
          }`}
        >
          <div className="flex items-center justify-between">
            <p
              className={`text-sm font-medium ${
                saveResult.type === "success"
                  ? "text-emerald-800"
                  : "text-red-800"
              }`}
            >
              {saveResult.type === "success" ? "Changes Saved" : "Save Failed"}
            </p>
            <button
              onClick={onDismissResult}
              aria-label="Dismiss save result notification"
              className="text-slate-400 hover:text-slate-600 text-sm"
            >
              Dismiss
            </button>
          </div>
          <p
            className={`text-xs mt-1 ${
              saveResult.type === "success"
                ? "text-emerald-600"
                : "text-red-600"
            }`}
          >
            {saveResult.message}
          </p>
        </div>
      )}
    </>
  );
}

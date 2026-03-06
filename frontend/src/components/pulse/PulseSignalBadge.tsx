interface PulseSignalBadgeProps {
  signal: string | null;
}

const SIGNAL_STYLES: Record<string, string> = {
  STRONG_OW: "bg-emerald-700 text-white",
  OVERWEIGHT: "bg-emerald-100 text-emerald-700",
  NEUTRAL: "bg-slate-100 text-slate-600",
  UNDERWEIGHT: "bg-red-100 text-red-700",
  STRONG_UW: "bg-red-700 text-white",
};

const SIGNAL_LABELS: Record<string, string> = {
  STRONG_OW: "Strong OW",
  OVERWEIGHT: "Overweight",
  NEUTRAL: "Neutral",
  UNDERWEIGHT: "Underweight",
  STRONG_UW: "Strong UW",
};

export default function PulseSignalBadge({ signal }: PulseSignalBadgeProps) {
  if (!signal) {
    return (
      <span className="inline-block rounded px-2.5 py-0.5 text-xs font-bold bg-slate-50 text-slate-400">
        --
      </span>
    );
  }

  const style =
    SIGNAL_STYLES[signal.toUpperCase()] ?? "bg-slate-100 text-slate-600";
  const label = SIGNAL_LABELS[signal.toUpperCase()] ?? signal;

  return (
    <span
      className={`inline-block rounded px-2.5 py-0.5 text-xs font-bold uppercase ${style}`}
    >
      {label}
    </span>
  );
}

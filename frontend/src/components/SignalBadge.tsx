interface SignalBadgeProps {
  signal: string;
}

const SIGNAL_STYLES: Record<string, string> = {
  OVERWEIGHT: "bg-emerald-600 text-white",
  ACCUMULATE: "bg-emerald-100 text-emerald-700",
  NEUTRAL: "bg-slate-100 text-slate-600",
  UNDERWEIGHT: "bg-amber-100 text-amber-700",
  AVOID: "bg-red-600 text-white",
};

export default function SignalBadge({ signal }: SignalBadgeProps) {
  const style =
    SIGNAL_STYLES[signal.toUpperCase()] ?? "bg-slate-100 text-slate-600";

  return (
    <span
      className={`inline-block rounded px-2.5 py-0.5 text-xs font-bold uppercase ${style}`}
    >
      {signal}
    </span>
  );
}

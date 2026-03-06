interface ActionBadgeProps {
  action: string;
}

const ACTION_STYLES: Record<string, string> = {
  ACCUMULATE: "bg-emerald-600 text-white",
  HOLD: "bg-amber-100 text-amber-700",
  REDUCE: "bg-orange-100 text-orange-700",
  EXIT: "bg-red-600 text-white",
};

export default function ActionBadge({ action }: ActionBadgeProps) {
  const style =
    ACTION_STYLES[action.toUpperCase()] ?? "bg-slate-100 text-slate-600";

  return (
    <span
      className={`inline-block rounded px-2.5 py-0.5 text-xs font-bold uppercase ${style}`}
    >
      {action}
    </span>
  );
}

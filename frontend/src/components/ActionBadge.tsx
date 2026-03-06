interface ActionBadgeProps {
  action: string;
}

const ACTION_STYLES: Record<string, string> = {
  BUY: "bg-emerald-600 text-white",
  SIP: "bg-emerald-100 text-emerald-700",
  HOLD_PLUS: "bg-blue-100 text-blue-700",
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

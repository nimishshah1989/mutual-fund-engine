interface TierBadgeProps {
  tier: string;
}

const TIER_STYLES: Record<string, string> = {
  CORE: "bg-emerald-600 text-white",
  QUALITY: "bg-blue-600 text-white",
  WATCH: "bg-amber-500 text-white",
  CAUTION: "bg-orange-500 text-white",
  EXIT: "bg-red-600 text-white",
};

export default function TierBadge({ tier }: TierBadgeProps) {
  const style = TIER_STYLES[tier.toUpperCase()] ?? "bg-slate-100 text-slate-600";

  return (
    <span
      className={`inline-block rounded px-2.5 py-0.5 text-xs font-bold uppercase ${style}`}
    >
      {tier}
    </span>
  );
}

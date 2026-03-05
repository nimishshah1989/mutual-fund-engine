interface StatCardProps {
  label: string;
  value: string;
  subtext?: string;
  /** When true the value renders in teal-600 instead of slate-800 */
  colored?: boolean;
  /** When true the value renders in red-600 (for critical/attention items) */
  alert?: boolean;
}

export default function StatCard({
  label,
  value,
  subtext,
  colored = false,
  alert = false,
}: StatCardProps) {
  let valueColor = "text-slate-800";
  if (colored) valueColor = "text-teal-600";
  if (alert) valueColor = "text-red-600";

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`text-2xl font-bold font-mono mt-1 ${valueColor}`}>
        {value}
      </p>
      {subtext && <p className="text-xs text-slate-400 mt-1">{subtext}</p>}
    </div>
  );
}

import MarketTicker from "./MarketTicker";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
}

export default function PageHeader({ title, subtitle }: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between mb-6">
      <div className="shrink-0">
        <h1 className="text-xl font-semibold text-slate-800">
          {title}
        </h1>
        {subtitle && <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
      <div className="hidden md:block">
        <MarketTicker />
      </div>
    </div>
  );
}

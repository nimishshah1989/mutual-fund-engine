import MarketTicker from "./MarketTicker";

interface PageHeaderProps {
  emoji: string;
  title: string;
  subtitle?: string;
}

export default function PageHeader({ emoji, title, subtitle }: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">
          {emoji} {title}
        </h1>
        {subtitle && <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
      <MarketTicker />
    </div>
  );
}

// Data Sources section. Documents the three primary data feeds
// used by the recommendation engine: Morningstar, FM signals,
// and portfolio holdings.

export default function DataSourcesSection() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="text-base font-semibold text-slate-800 mb-3">
        Data Sources
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <DataSourceCard
          title="Morningstar API"
          description="Fund master data, trailing returns, risk statistics (Sharpe, Alpha, Beta, etc.), sector exposure breakdowns, and category benchmarks. 7 API endpoints per fund fetched concurrently during ingestion."
        />
        <DataSourceCard
          title="Fund Manager Signals"
          description="Sector-level directional views (OVERWEIGHT to AVOID) across 11 Morningstar sectors, set by the fund manager through the FM Signals page. All changes are logged in the signal change audit trail."
        />
        <DataSourceCard
          title="Portfolio Holdings"
          description="Fund portfolio composition from Morningstar Global Stock Sector Breakdown API, showing sector-wise allocation percentages across 11 sectors. Used for FSAS alignment scoring on shortlisted funds only."
        />
      </div>
    </div>
  );
}

interface DataSourceCardProps {
  title: string;
  description: string;
}

function DataSourceCard({ title, description }: DataSourceCardProps) {
  return (
    <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
      <p className="text-sm font-semibold text-slate-800">{title}</p>
      <p className="text-xs text-slate-500 mt-1">{description}</p>
    </div>
  );
}

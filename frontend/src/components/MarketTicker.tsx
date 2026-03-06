/**
 * Static market ticker strip shown at the top of every page.
 * TODO: Connect to live index API (yfinance via backend proxy or Kite Connect)
 * to replace placeholder values with real-time market data.
 */
export default function MarketTicker() {
  return (
    <div className="flex items-center gap-6 text-xs">
      <div>
        <span className="text-slate-400">NIFTY 50</span>
        <span className="ml-1 font-mono font-semibold text-emerald-600">
          22,847
        </span>
        <span className="ml-1 text-emerald-600">+1.24%</span>
      </div>
      <div>
        <span className="text-slate-400">SENSEX</span>
        <span className="ml-1 font-mono font-semibold text-emerald-600">
          75,313
        </span>
        <span className="ml-1 text-emerald-600">+1.18%</span>
      </div>
      <div>
        <span className="text-slate-400">NIFTY MID</span>
        <span className="ml-1 font-mono font-semibold text-red-500">
          53,215
        </span>
        <span className="ml-1 text-red-500">{"\u2212"}0.32%</span>
      </div>
      <div>
        <span className="text-slate-400">10Y G-Sec</span>
        <span className="ml-1 font-mono font-semibold text-slate-700">
          6.82%
        </span>
        <span className="ml-1 text-red-500">{"\u2212"}3bps</span>
      </div>
      <div className="flex items-center gap-1">
        <span className="w-2 h-2 rounded-full bg-slate-300" />
        <span className="text-slate-400">Market Closed</span>
      </div>
    </div>
  );
}

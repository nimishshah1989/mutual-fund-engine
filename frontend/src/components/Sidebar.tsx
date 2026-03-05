"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavItem {
  emoji: string;
  label: string;
  href: string;
}

const NAV_ITEMS: NavItem[] = [
  { emoji: "\uD83D\uDCCA", label: "Dashboard", href: "/" },
  { emoji: "\uD83C\uDFC6", label: "Fund Scoreboard", href: "/funds" },
  { emoji: "\uD83D\uDCC8", label: "FM Signals", href: "/signals" },
  { emoji: "\uD83D\uDCD6", label: "Methodology", href: "/methodology" },
  { emoji: "\u2699\uFE0F", label: "System", href: "/system" },
];

export default function Sidebar() {
  const pathname = usePathname();

  function isActive(href: string): boolean {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  }

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-56 bg-white border-r border-slate-200 flex flex-col z-40">
      {/* Brand */}
      <div className="px-4 py-5">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-teal-600 flex items-center justify-center text-white font-bold text-sm">
            J
          </div>
          <div>
            <p className="text-sm font-bold text-slate-800 tracking-wide">
              JHAVERI
            </p>
            <p className="text-[10px] text-slate-400 tracking-widest uppercase">
              Intelligence Platform
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 mt-2 space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={
                active
                  ? "flex items-center gap-3 w-full px-4 py-2.5 text-sm text-white bg-teal-600 rounded-r-lg font-medium"
                  : "flex items-center gap-3 w-full px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-50 hover:text-slate-800 transition-colors rounded-r-lg"
              }
            >
              <span className="text-base">{item.emoji}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* User section */}
      <div className="px-4 py-3 border-t border-slate-200">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-teal-100 flex items-center justify-center">
            <span className="text-xs font-semibold text-teal-700">NS</span>
          </div>
          <div>
            <p className="text-sm font-medium text-slate-800">Nimish Shah</p>
            <p className="text-xs text-slate-400">Admin</p>
          </div>
        </div>
      </div>
    </aside>
  );
}

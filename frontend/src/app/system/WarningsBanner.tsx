"use client";

interface WarningsBannerProps {
  warnings: string[];
}

/**
 * Amber-themed banner displaying system warnings.
 * Renders nothing when there are no warnings.
 */
export default function WarningsBanner({ warnings }: WarningsBannerProps) {
  if (warnings.length === 0) return null;

  return (
    <div className="mb-6 bg-amber-50 border border-amber-200 rounded-xl p-4">
      <div className="flex items-start gap-3">
        <span className="text-amber-600 text-lg leading-none mt-0.5">
          &#x26A0;&#xFE0F;
        </span>
        <div>
          <p className="text-sm font-semibold text-amber-800">
            System Warnings ({warnings.length})
          </p>
          <ul className="mt-1 space-y-0.5">
            {warnings.map((warning, idx) => (
              <li key={idx} className="text-sm text-amber-700">
                {warning}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

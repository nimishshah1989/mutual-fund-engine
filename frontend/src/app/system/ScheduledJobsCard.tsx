"use client";

import { formatDate } from "@/lib/formatters";
import type { SchedulerJob } from "@/types/api";

interface ScheduledJobsCardProps {
  jobs: SchedulerJob[];
}

/**
 * Card listing all scheduled background jobs with their next run times.
 */
export default function ScheduledJobsCard({ jobs }: ScheduledJobsCardProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="text-base font-semibold text-slate-800 mb-4">
        Scheduled Jobs
      </h3>
      {jobs.length === 0 ? (
        <p className="text-sm text-slate-400 text-center py-4">
          No scheduled jobs
        </p>
      ) : (
        <div className="space-y-2">
          {jobs.map((job) => (
            <div
              key={job.id}
              className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0"
            >
              <div>
                <p className="text-sm font-medium text-slate-800">
                  {job.name}
                </p>
                <p className="text-xs text-slate-400 font-mono">
                  {job.id}
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs text-slate-500">Next run</p>
                <p className="text-xs font-mono text-slate-700">
                  {formatDate(job.next_run)}
                </p>
                {job.pending && (
                  <span className="inline-block mt-0.5 rounded px-2 py-0.5 text-xs font-bold bg-amber-100 text-amber-700 uppercase">
                    Pending
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

'use client';

import { Activity } from 'lucide-react';
import { usePolling } from '@/hooks/usePolling';
import { StatCard } from '@/components/ui/StatCard';
import { Card, CardContent } from '@/components/ui/card';
import { ErrorBanner } from '@/components/shared/ErrorBanner';
import { cn } from '@/lib/utils';
import type { AutomationStats } from '@/lib/types';

export default function OverviewPage() {
  const { data: stats, message, loading, unreachable } = usePolling<AutomationStats>('/api/stats', 15000);

  return (
    <div className="w-full px-6 py-10 md:px-10">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-white">Overview</h1>
        <p className="mt-1 text-sm text-slate-500">System-wide status of the automation server.</p>
      </div>

      {unreachable && <ErrorBanner message={message ?? undefined} />}

      {!unreachable && !loading && !stats && (
        <ErrorBanner message={message ?? 'Could not load system statistics.'} />
      )}

      {stats && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            <StatCard value={String(stats.tasks.total)} label="Total Tasks" />
            <StatCard value={String(stats.tasks.running)} label="Running" highlight />
            <StatCard value={String(stats.tasks.completed)} label="Completed" />
            <StatCard value={String(stats.tasks.stopped)} label="Stopped" />
            <StatCard value={String(stats.tasks.error)} label="Errored" />
          </div>

          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <Card className={cn('glass-card-dark rounded-[1.5rem]')}>
              <CardContent className="px-6">
                <div className="mb-4 flex items-center gap-2">
                  <Activity className="h-4 w-4 text-indigo-400" />
                  <h2 className="text-sm font-semibold text-white">Success rate</h2>
                </div>
                <p className="text-3xl font-semibold text-white">{stats.success_rate}</p>
              </CardContent>
            </Card>

            <Card className={cn('glass-card-dark rounded-[1.5rem]')}>
              <CardContent className="px-6">
                <h2 className="mb-4 text-sm font-semibold text-white">Currently scraping</h2>
                {stats.active_scraping.industries.length === 0 ? (
                  <p className="text-sm text-slate-500">Nothing running right now.</p>
                ) : (
                  <div className="space-y-2 text-sm text-slate-400">
                    <p>
                      <span className="text-slate-500">Industries:</span> {stats.active_scraping.industries.join(', ')}
                    </p>
                    <p>
                      <span className="text-slate-500">Locations:</span> {stats.active_scraping.locations.join(', ')}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

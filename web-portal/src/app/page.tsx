'use client';

import type { ReactNode } from 'react';
import { usePolling } from '@/hooks/usePolling';
import { StatCard } from '@/components/ui/StatCard';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ErrorBanner } from '@/components/shared/ErrorBanner';
import { toneClass, type Tone } from '@/lib/status';
import type { AutomationStats, DashboardStats, LeadStatus } from '@/lib/types';

const STATUS_TONE: Record<LeadStatus, Tone> = {
  new: 'slate',
  contacted: 'indigo',
  replied: 'amber',
  interested: 'amber',
  won: 'emerald',
  lost: 'red',
};

const STATUS_ORDER: LeadStatus[] = ['new', 'contacted', 'replied', 'interested', 'won', 'lost'];

function Section({ title, description, children }: { title: string; description?: string; children: ReactNode }) {
  return (
    <section>
      <div className="mb-6 flex items-baseline gap-3">
        <h2 className="text-xs font-semibold tracking-widest text-indigo-400/90 uppercase">{title}</h2>
        {description && <p className="text-sm text-slate-500">{description}</p>}
      </div>
      {children}
    </section>
  );
}

function SubLabel({ children }: { children: ReactNode }) {
  return <h3 className="mb-3 text-xs font-medium tracking-wide text-slate-500 uppercase">{children}</h3>;
}

function BarList({ items, total }: { items: { label: string; count: number }[]; total: number }) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">Nothing scraped yet.</p>;
  }
  const max = Math.max(...items.map((i) => i.count), 1);
  return (
    <div className="space-y-2.5">
      {items.map((item) => (
        <div key={item.label}>
          <div className="mb-1 flex items-center justify-between text-xs">
            <span className="text-slate-300">{item.label}</span>
            <span className="text-slate-500">
              {item.count} {total > 0 && `(${Math.round((item.count / total) * 100)}%)`}
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-white/[0.04]">
            <div
              className="h-full rounded-full bg-indigo-500/60"
              style={{ width: `${(item.count / max) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function OverviewPage() {
  const { data: stats, message, loading, unreachable } = usePolling<AutomationStats>('/api/stats', 15000);
  const { data: dashboard } = usePolling<DashboardStats>('/api/dashboard-stats', 15000);

  return (
    <div className="w-full space-y-12 px-6 py-10 md:px-10">
      {unreachable && <ErrorBanner message={message ?? undefined} />}
      {!unreachable && !loading && !stats && <ErrorBanner message={message ?? 'Could not load system statistics.'} />}

      {stats && (
        <Section title="Automation">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
            <StatCard value={String(stats.tasks.total)} label="Total Tasks" />
            <StatCard value={String(stats.tasks.running)} label="Running" highlight />
            <StatCard value={String(stats.tasks.completed)} label="Completed" />
            <StatCard value={String(stats.tasks.stopped)} label="Stopped" />
            <StatCard value={String(stats.tasks.error)} label="Errored" />
            <StatCard value={stats.success_rate} label="Success rate" />
          </div>
          <p className="mt-5 text-sm">
            {stats.active_scraping.industries.length === 0 ? (
              <span className="text-slate-500">Nothing scraping right now.</span>
            ) : (
              <span className="text-slate-400">
                Currently scraping <span className="text-slate-200">{stats.active_scraping.industries.join(', ')}</span> in{' '}
                <span className="text-slate-200">{stats.active_scraping.locations.join(', ')}</span>.
              </span>
            )}
          </p>
        </Section>
      )}

      {dashboard && (
        <>
          <Section
            title="Leads"
            description={`${dashboard.leads.total} lead${dashboard.leads.total === 1 ? '' : 's'} scraped in total.`}
          >
            <div className="grid grid-cols-3 gap-4">
              <StatCard value={String(dashboard.leads.by_score_tier.hot)} label="Hot prospects" highlight />
              <StatCard value={String(dashboard.leads.by_score_tier.warm)} label="Warm prospects" />
              <StatCard value={String(dashboard.leads.by_score_tier.cool)} label="Cool prospects" />
            </div>

            <div className="mt-6 flex flex-col gap-6 md:flex-row">
              <div className="flex-1">
                <SubLabel>Pipeline</SubLabel>
                <div className="flex flex-wrap gap-1.5">
                  {STATUS_ORDER.map((s) => (
                    <Badge key={s} variant="outline" className={toneClass(STATUS_TONE[s])}>
                      {s.charAt(0).toUpperCase() + s.slice(1)}: {dashboard.leads.by_status[s]}
                    </Badge>
                  ))}
                </div>
                <div className="mt-3 space-y-1 text-xs text-slate-500">
                  <p>{dashboard.leads.with_email} with an email on file</p>
                  <p>{dashboard.leads.unclaimed} unclaimed Google Business listings</p>
                </div>
              </div>

              <Separator orientation="vertical" className="hidden h-auto bg-white/10 md:block" />

              <div className="flex-1">
                <SubLabel>Email sends</SubLabel>
                {dashboard.outreach.total === 0 ? (
                  <p className="text-sm text-slate-500">No outreach emails sent yet.</p>
                ) : (
                  <div className="flex items-baseline gap-6">
                    <div>
                      <p className="text-3xl font-semibold text-emerald-400">{dashboard.outreach.sent}</p>
                      <p className="text-xs text-slate-500">Sent</p>
                    </div>
                    <div>
                      <p className="text-3xl font-semibold text-red-400">{dashboard.outreach.failed}</p>
                      <p className="text-xs text-slate-500">Failed</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </Section>

          <Section title="Coverage" description="Where leads are coming from.">
            <div className="flex flex-col gap-8 md:flex-row">
              <div className="flex-1">
                <SubLabel>Top industries</SubLabel>
                <BarList
                  items={dashboard.top_industries.map((i) => ({ label: i.industry, count: i.count }))}
                  total={dashboard.leads.total}
                />
              </div>
              <Separator orientation="vertical" className="hidden h-auto bg-white/10 md:block" />
              <div className="flex-1">
                <SubLabel>Top locations</SubLabel>
                <BarList
                  items={dashboard.top_locations.map((l) => ({ label: l.location, count: l.count }))}
                  total={dashboard.leads.total}
                />
              </div>
            </div>
          </Section>
        </>
      )}
    </div>
  );
}

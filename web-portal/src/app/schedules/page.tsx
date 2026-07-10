'use client';

import { useState } from 'react';
import { Plus } from 'lucide-react';
import { usePolling } from '@/hooks/usePolling';
import { Button } from '@/components/ui/button';
import { ErrorBanner } from '@/components/shared/ErrorBanner';
import { ScheduleTable } from '@/components/schedules/ScheduleTable';
import { ScheduleFormModal } from '@/components/schedules/ScheduleFormModal';
import type { Schedule, SchedulesResponse } from '@/lib/types';

export default function SchedulesPage() {
  const { data, message, loading, unreachable, refetch } = usePolling<SchedulesResponse>('/api/schedules', 15000);
  const [createOpen, setCreateOpen] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<Schedule | null>(null);

  return (
    <div className="w-full px-6 py-8 md:px-10">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-white">Schedules</h1>
          <p className="mt-1 text-sm text-slate-500">
            Re-run a scrape automatically on a recurring interval instead of starting it by hand every time.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="h-3.5 w-3.5" />
          New schedule
        </Button>
      </div>

      {unreachable && <ErrorBanner message={message ?? undefined} />}

      {!unreachable && !loading && !data && <ErrorBanner message={message ?? 'Could not load schedules.'} />}
      {data && <ScheduleTable schedules={data.schedules} onChanged={refetch} onEdit={setEditingSchedule} />}

      <ScheduleFormModal createOpen={createOpen} onClose={() => setCreateOpen(false)} onSaved={refetch} />
      <ScheduleFormModal editingSchedule={editingSchedule} onClose={() => setEditingSchedule(null)} onSaved={refetch} />
    </div>
  );
}

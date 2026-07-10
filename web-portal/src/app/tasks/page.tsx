'use client';

import { useState } from 'react';
import { Square, ChevronLeft, ChevronRight } from 'lucide-react';
import { usePolling } from '@/hooks/usePolling';
import { Button } from '@/components/ui/button';
import { ErrorBanner } from '@/components/shared/ErrorBanner';
import { NewTaskForm } from '@/components/tasks/NewTaskForm';
import { TaskTable } from '@/components/tasks/TaskTable';
import { postJson } from '@/lib/client';
import type { TasksPage } from '@/lib/types';

const PAGE_SIZE = 20;

export default function TasksPage() {
  const [page, setPage] = useState(0);
  const { data, message, loading, unreachable, refetch } = usePolling<TasksPage>(
    `/api/tasks?limit=${PAGE_SIZE}&offset=${page * PAGE_SIZE}`,
    3000
  );
  const [stoppingAll, setStoppingAll] = useState(false);

  async function stopAll() {
    setStoppingAll(true);
    await postJson('/api/tasks/stop-all');
    setStoppingAll(false);
    refetch();
  }

  const runningCount = data ? data.tasks.filter((t) => t.running).length : 0;
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="w-full px-6 py-8 md:px-10">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-white">Tasks</h1>
          <p className="mt-1 text-sm text-slate-500">
            {data ? `${data.total} task${data.total === 1 ? '' : 's'}. ` : ''}Start, monitor, and stop scrape tasks.
          </p>
        </div>
        {runningCount > 0 && (
          <Button variant="destructive" disabled={stoppingAll} onClick={stopAll}>
            <Square className="h-3.5 w-3.5" />
            {stoppingAll ? 'Stopping…' : `Stop all (${runningCount})`}
          </Button>
        )}
      </div>

      {unreachable && <ErrorBanner message={message ?? undefined} />}

      <div className="mb-6">
        <NewTaskForm onStarted={refetch} />
      </div>

      {!unreachable && !loading && !data && <ErrorBanner message={message ?? 'Could not load tasks.'} />}
      {data && <TaskTable tasks={data.tasks} onChanged={refetch} />}

      {data && data.total > PAGE_SIZE && (
        <div className="mt-4 flex items-center justify-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            disabled={page === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            Prev
          </Button>
          <span className="text-xs text-slate-500">
            Page {page + 1} of {totalPages}
          </span>
          <Button
            variant="secondary"
            size="sm"
            disabled={page + 1 >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
            <ChevronRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      )}
    </div>
  );
}

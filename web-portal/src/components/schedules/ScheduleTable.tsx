'use client';

import { useState } from 'react';
import { CalendarClock, Pencil, Trash2, Play } from 'lucide-react';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/shared/EmptyState';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { deleteJson, patchJson, postJson } from '@/lib/client';
import { toneClass } from '@/lib/status';
import type { Schedule } from '@/lib/types';

interface ScheduleTableProps {
  schedules: Schedule[];
  onChanged: () => void;
  onEdit: (schedule: Schedule) => void;
}

function formatIn(iso: string): string {
  const diffMs = new Date(iso).getTime() - Date.now();
  if (diffMs <= 0) return 'due now';
  const hours = Math.round(diffMs / (1000 * 60 * 60));
  if (hours < 1) return 'in <1h';
  if (hours < 24) return `in ${hours}h`;
  return `in ${Math.round(hours / 24)}d`;
}

export function ScheduleTable({ schedules, onChanged, onEdit }: ScheduleTableProps) {
  const [busyId, setBusyId] = useState<number | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Schedule | null>(null);

  async function remove(id: number) {
    setBusyId(id);
    await deleteJson(`/api/schedules/${id}`);
    setBusyId(null);
    onChanged();
  }

  async function toggleEnabled(schedule: Schedule) {
    setBusyId(schedule.id);
    await patchJson(`/api/schedules/${schedule.id}`, { enabled: !schedule.enabled });
    setBusyId(null);
    onChanged();
  }

  async function runNow(id: number) {
    setBusyId(id);
    await postJson(`/api/schedules/${id}/run-now`);
    setBusyId(null);
    onChanged();
  }

  if (schedules.length === 0) {
    return (
      <EmptyState
        icon={<CalendarClock className="h-5 w-5" />}
        title="No schedules yet"
        description="Create one above to have a scrape re-run automatically on a recurring interval."
      />
    );
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-8">On</TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Industry</TableHead>
            <TableHead>Locations</TableHead>
            <TableHead>Repeats</TableHead>
            <TableHead>Next run</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {schedules.map((schedule) => (
            <TableRow key={schedule.id}>
              <TableCell>
                <Checkbox
                  checked={schedule.enabled}
                  onCheckedChange={() => toggleEnabled(schedule)}
                  disabled={busyId === schedule.id}
                  aria-label={`${schedule.enabled ? 'Disable' : 'Enable'} ${schedule.name}`}
                />
              </TableCell>
              <TableCell className="font-medium text-slate-200">{schedule.name}</TableCell>
              <TableCell className="text-slate-400">{schedule.industry}</TableCell>
              <TableCell className="text-slate-400">{schedule.locations.join(', ')}</TableCell>
              <TableCell className="text-slate-400">
                {schedule.interval_hours % 24 === 0
                  ? `every ${schedule.interval_hours / 24}d`
                  : `every ${schedule.interval_hours}h`}
              </TableCell>
              <TableCell>
                {schedule.enabled ? (
                  <Badge variant="outline" className={toneClass('indigo')}>
                    {formatIn(schedule.next_run_at)}
                  </Badge>
                ) : (
                  <span className="text-slate-600">paused</span>
                )}
              </TableCell>
              <TableCell>
                <div className="flex items-center justify-end gap-1.5">
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    disabled={busyId === schedule.id}
                    onClick={() => runNow(schedule.id)}
                    aria-label="Run now"
                  >
                    <Play className="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon-sm" onClick={() => onEdit(schedule)} aria-label="Edit schedule">
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className="text-red-400 hover:text-red-300"
                    disabled={busyId === schedule.id}
                    onClick={() => setPendingDelete(schedule)}
                    aria-label="Delete schedule"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <ConfirmDialog
        open={pendingDelete != null}
        onOpenChange={(open) => !open && setPendingDelete(null)}
        title="Delete schedule"
        description={`Permanently delete "${pendingDelete?.name}"? This cannot be undone.`}
        confirmLabel="Delete"
        onConfirm={() => pendingDelete && remove(pendingDelete.id)}
      />
    </>
  );
}

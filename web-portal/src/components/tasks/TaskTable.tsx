'use client';

import { useState } from 'react';
import { Square, Trash2, ListTodo } from 'lucide-react';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/shared/EmptyState';
import { postJson, deleteJson } from '@/lib/client';
import { TASK_STATUS_TONE, toneClass } from '@/lib/status';
import type { Task } from '@/lib/types';

interface TaskTableProps {
  tasks: Task[];
  onChanged: () => void;
}

export function TaskTable({ tasks, onChanged }: TaskTableProps) {
  const [busyId, setBusyId] = useState<string | null>(null);

  async function stopTask(id: string) {
    setBusyId(id);
    await postJson(`/api/tasks/${id}/stop`);
    setBusyId(null);
    onChanged();
  }

  async function deleteTask(id: string) {
    setBusyId(id);
    await deleteJson(`/api/tasks/${id}`);
    setBusyId(null);
    onChanged();
  }

  if (tasks.length === 0) {
    return (
      <EmptyState
        icon={<ListTodo className="h-5 w-5" />}
        title="No tasks yet"
        description="Start a scrape above to see it show up here."
      />
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Status</TableHead>
          <TableHead>Industry</TableHead>
          <TableHead>Locations</TableHead>
          <TableHead>Limit / location</TableHead>
          <TableHead>Error</TableHead>
          <TableHead />
        </TableRow>
      </TableHeader>
      <TableBody>
        {tasks.map((task) => (
          <TableRow key={task.id}>
            <TableCell>
              <Badge variant="outline" className={toneClass(TASK_STATUS_TONE[task.status])}>
                {task.status === 'running' && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-400" />}
                {task.status}
              </Badge>
            </TableCell>
            <TableCell className="font-medium text-slate-200">{task.config.industry}</TableCell>
            <TableCell>{task.config.locations.join(', ')}</TableCell>
            <TableCell>{task.config.limit_per_location === -1 ? 'Unlimited' : task.config.limit_per_location}</TableCell>
            <TableCell className="max-w-xs truncate text-red-400">{task.error ?? '—'}</TableCell>
            <TableCell>
              <div className="flex items-center justify-end gap-1.5">
                {task.running ? (
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={busyId === task.id}
                    onClick={() => stopTask(task.id)}
                  >
                    <Square className="h-3 w-3" />
                    {busyId === task.id ? 'Stopping…' : 'Stop'}
                  </Button>
                ) : (
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className="text-red-400 hover:text-red-300"
                    disabled={busyId === task.id}
                    onClick={() => deleteTask(task.id)}
                    aria-label="Delete task"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

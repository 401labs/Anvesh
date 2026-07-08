'use client';

import { useState } from 'react';
import { KeyRound, Ban, Trash2, BarChart3, Pencil } from 'lucide-react';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/shared/EmptyState';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { postJson, deleteJson } from '@/lib/client';
import { toneClass, type Tone } from '@/lib/status';
import type { ApiKey, ApiKeyTier } from '@/lib/types';

const TIER_TONE: Record<ApiKeyTier, Tone> = {
  free: 'slate',
  pro: 'indigo',
  enterprise: 'emerald',
};

interface KeyTableProps {
  keys: ApiKey[];
  onChanged: () => void;
  onViewUsage: (id: number) => void;
  onEdit: (key: ApiKey) => void;
}

export function KeyTable({ keys, onChanged, onViewUsage, onEdit }: KeyTableProps) {
  const [busyId, setBusyId] = useState<number | null>(null);
  const [pendingDelete, setPendingDelete] = useState<ApiKey | null>(null);

  async function revoke(id: number) {
    setBusyId(id);
    await postJson(`/api/keys/${id}/revoke`);
    setBusyId(null);
    onChanged();
  }

  async function remove(id: number) {
    setBusyId(id);
    await deleteJson(`/api/keys/${id}`);
    setBusyId(null);
    onChanged();
  }

  if (keys.length === 0) {
    return (
      <EmptyState
        icon={<KeyRound className="h-5 w-5" />}
        title="No API keys yet"
        description="Create one above to start calling the automation API."
      />
    );
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Prefix</TableHead>
            <TableHead>Tier</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Created</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {keys.map((key) => (
            <TableRow key={key.id}>
              <TableCell className="font-medium text-slate-200">{key.name}</TableCell>
              <TableCell>
                <code className="text-xs text-slate-500">{key.key_prefix}…</code>
              </TableCell>
              <TableCell>
                <Badge variant="outline" className={toneClass(TIER_TONE[key.tier])}>
                  {key.tier}
                </Badge>
              </TableCell>
              <TableCell>
                <Badge variant="outline" className={toneClass(key.is_active ? 'emerald' : 'red')}>
                  {key.is_active ? 'Active' : 'Revoked'}
                </Badge>
              </TableCell>
              <TableCell className="text-slate-500">{new Date(key.created_at).toLocaleDateString()}</TableCell>
              <TableCell>
                <div className="flex items-center justify-end gap-1.5">
                  <Button variant="ghost" size="icon-sm" onClick={() => onEdit(key)} aria-label="Edit key">
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon-sm" onClick={() => onViewUsage(key.id)} aria-label="View usage">
                    <BarChart3 className="h-3.5 w-3.5" />
                  </Button>
                  {key.is_active && (
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      disabled={busyId === key.id}
                      onClick={() => revoke(key.id)}
                      aria-label="Revoke key"
                    >
                      <Ban className="h-3.5 w-3.5" />
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className="text-red-400 hover:text-red-300"
                    disabled={busyId === key.id}
                    onClick={() => setPendingDelete(key)}
                    aria-label="Delete key"
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
        title="Delete API key"
        description={`Permanently delete "${pendingDelete?.name}"? This cannot be undone.`}
        confirmLabel="Delete"
        onConfirm={() => pendingDelete && remove(pendingDelete.id)}
      />
    </>
  );
}

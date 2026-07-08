'use client';

import { useState } from 'react';
import { Users, Globe, Mail, Star, Pencil, Trash2 } from 'lucide-react';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { EmptyState } from '@/components/shared/EmptyState';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { deleteJson } from '@/lib/client';
import { toneClass } from '@/lib/status';
import type { Lead } from '@/lib/types';

interface LeadsTableProps {
  leads: Lead[];
  selectedIds: Set<number>;
  onToggleSelect: (id: number) => void;
  onToggleSelectAll: () => void;
  onEdit: (lead: Lead) => void;
  onChanged: () => void;
}

export function LeadsTable({ leads, selectedIds, onToggleSelect, onToggleSelectAll, onEdit, onChanged }: LeadsTableProps) {
  const [busyId, setBusyId] = useState<number | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Lead | null>(null);

  async function remove(id: number) {
    setBusyId(id);
    await deleteJson(`/api/leads/${id}`);
    setBusyId(null);
    onChanged();
  }

  if (leads.length === 0) {
    return (
      <EmptyState
        icon={<Users className="h-5 w-5" />}
        title="No leads yet"
        description="Start a scrape task, or add one manually, to see it show up here."
      />
    );
  }

  const allSelected = leads.length > 0 && leads.every((l) => selectedIds.has(l.id));

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-8">
              <Checkbox
                checked={allSelected}
                onCheckedChange={onToggleSelectAll}
                aria-label="Select all leads on this page"
              />
            </TableHead>
            <TableHead>Business</TableHead>
            <TableHead>Category</TableHead>
            <TableHead>Location</TableHead>
            <TableHead>Rating</TableHead>
            <TableHead>Website</TableHead>
            <TableHead>Phone</TableHead>
            <TableHead>Email</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {leads.map((lead) => (
            <TableRow key={lead.id}>
              <TableCell>
                <Checkbox
                  checked={selectedIds.has(lead.id)}
                  onCheckedChange={() => onToggleSelect(lead.id)}
                  aria-label={`Select ${lead.business_name}`}
                />
              </TableCell>
              <TableCell className="font-medium text-slate-200">
                {lead.business_name}
                {lead.is_claimed === false && (
                  <Badge variant="outline" className={`ml-2 ${toneClass('emerald')}`}>
                    Unclaimed
                  </Badge>
                )}
              </TableCell>
              <TableCell>{lead.category ?? '—'}</TableCell>
              <TableCell>{lead.location}</TableCell>
              <TableCell>
                {lead.rating != null ? (
                  <span className="flex items-center gap-1">
                    <Star className="h-3 w-3 text-amber-400" />
                    {lead.rating} ({lead.review_count ?? 0})
                  </span>
                ) : (
                  '—'
                )}
              </TableCell>
              <TableCell>
                {lead.has_website ? (
                  <a
                    href={lead.website_url ?? '#'}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300"
                  >
                    <Globe className="h-3 w-3" /> Visit
                  </a>
                ) : (
                  <span className="text-slate-600">None</span>
                )}
              </TableCell>
              <TableCell>{lead.phone ?? '—'}</TableCell>
              <TableCell>
                {lead.email ? (
                  <a
                    href={`mailto:${lead.email}`}
                    className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300"
                  >
                    <Mail className="h-3 w-3" />
                    <span className="max-w-[160px] truncate">{lead.email}</span>
                  </a>
                ) : (
                  '—'
                )}
              </TableCell>
              <TableCell>
                <div className="flex items-center justify-end gap-1.5">
                  <Button variant="ghost" size="icon-sm" onClick={() => onEdit(lead)} aria-label="Edit lead">
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className="text-red-400 hover:text-red-300"
                    disabled={busyId === lead.id}
                    onClick={() => setPendingDelete(lead)}
                    aria-label="Delete lead"
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
        title="Delete lead"
        description={`Permanently delete "${pendingDelete?.business_name}"? This cannot be undone.`}
        confirmLabel="Delete"
        onConfirm={() => pendingDelete && remove(pendingDelete.id)}
      />
    </>
  );
}

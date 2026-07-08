'use client';

import { useEffect, useState } from 'react';
import { Download, ChevronLeft, ChevronRight, Plus, Trash2, X } from 'lucide-react';
import { usePolling } from '@/hooks/usePolling';
import { Button } from '@/components/ui/button';
import { ErrorBanner } from '@/components/shared/ErrorBanner';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { LeadsTable } from '@/components/leads/LeadsTable';
import { LeadFormModal } from '@/components/leads/LeadFormModal';
import { LeadsFilterBar } from '@/components/leads/LeadsFilterBar';
import { postJson } from '@/lib/client';
import { leadFiltersToQuery, EMPTY_LEAD_FILTERS } from '@/lib/leadQuery';
import type { Lead, LeadFilters, LeadsPage } from '@/lib/types';

const PAGE_SIZE = 20;

export default function LeadsPage() {
  const [page, setPage] = useState(0);
  const [filters, setFilters] = useState<LeadFilters>(EMPTY_LEAD_FILTERS);
  const filterQuery = leadFiltersToQuery(filters);

  const { data, message, loading, unreachable, refetch } = usePolling<LeadsPage>(
    `/api/leads?limit=${PAGE_SIZE}&offset=${page * PAGE_SIZE}${filterQuery ? `&${filterQuery}` : ''}`
  );
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [createOpen, setCreateOpen] = useState(false);
  const [editingLead, setEditingLead] = useState<Lead | null>(null);
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [confirmBulkDelete, setConfirmBulkDelete] = useState(false);

  // Selection is page-scoped — drop it when the page or underlying data changes.
  useEffect(() => {
    setSelectedIds(new Set());
  }, [page]);

  // Changing filters invalidates the current page (result set shrinks/reorders).
  function handleFiltersChange(next: LeadFilters) {
    setFilters(next);
    setPage(0);
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const exportHref = `/api/leads/export${filterQuery ? `?${filterQuery}` : ''}`;

  function toggleSelect(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (!data) return;
    setSelectedIds((prev) => {
      const allSelected = data.leads.every((l) => prev.has(l.id));
      return allSelected ? new Set() : new Set(data.leads.map((l) => l.id));
    });
  }

  async function bulkDelete() {
    if (selectedIds.size === 0) return;
    setBulkDeleting(true);
    await postJson('/api/leads/bulk-delete', { ids: Array.from(selectedIds) });
    setBulkDeleting(false);
    setSelectedIds(new Set());
    refetch();
  }

  return (
    <div className="w-full px-6 py-10 md:px-10">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-white">Leads</h1>
          <p className="mt-1 text-sm text-slate-500">
            {data
              ? `${data.total} lead${data.total === 1 ? '' : 's'}${filterQuery ? ' matching filters' : ' scraped so far'}.`
              : 'Browse scraped leads.'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => setCreateOpen(true)}>
            <Plus className="h-3.5 w-3.5" />
            Add Lead
          </Button>
          <a href={exportHref}>
            <Button variant="secondary">
              <Download className="h-3.5 w-3.5" />
              Export CSV{filterQuery ? ' (filtered)' : ''}
            </Button>
          </a>
        </div>
      </div>

      {unreachable && <ErrorBanner message={message ?? undefined} />}

      <LeadsFilterBar filters={filters} onChange={handleFiltersChange} />

      {selectedIds.size > 0 && (
        <div className="mb-4 flex items-center justify-between rounded-2xl border border-indigo-500/20 bg-indigo-500/[0.06] px-4 py-3">
          <span className="text-sm text-indigo-200">{selectedIds.size} selected</span>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => setSelectedIds(new Set())}>
              <X className="h-3.5 w-3.5" />
              Clear
            </Button>
            <Button
              variant="destructive"
              size="sm"
              disabled={bulkDeleting}
              onClick={() => setConfirmBulkDelete(true)}
            >
              <Trash2 className="h-3.5 w-3.5" />
              {bulkDeleting ? 'Deleting…' : 'Delete selected'}
            </Button>
          </div>
        </div>
      )}

      {!unreachable && !loading && !data && <ErrorBanner message={message ?? 'Could not load leads.'} />}
      {data && (
        <LeadsTable
          leads={data.leads}
          selectedIds={selectedIds}
          onToggleSelect={toggleSelect}
          onToggleSelectAll={toggleSelectAll}
          onEdit={setEditingLead}
          onChanged={refetch}
        />
      )}

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

      <LeadFormModal createOpen={createOpen} onClose={() => setCreateOpen(false)} onSaved={refetch} />
      <LeadFormModal editingLead={editingLead} onClose={() => setEditingLead(null)} onSaved={refetch} />
      <ConfirmDialog
        open={confirmBulkDelete}
        onOpenChange={setConfirmBulkDelete}
        title="Delete leads"
        description={`Permanently delete ${selectedIds.size} selected lead(s)? This cannot be undone.`}
        confirmLabel="Delete"
        onConfirm={bulkDelete}
      />
    </div>
  );
}

'use client';

import { useState } from 'react';
import { FileText, Pencil, Trash2 } from 'lucide-react';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/shared/EmptyState';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { deleteJson } from '@/lib/client';
import type { EmailTemplate } from '@/lib/types';

interface TemplateTableProps {
  templates: EmailTemplate[];
  onChanged: () => void;
  onEdit: (template: EmailTemplate) => void;
}

export function TemplateTable({ templates, onChanged, onEdit }: TemplateTableProps) {
  const [busyId, setBusyId] = useState<number | null>(null);
  const [pendingDelete, setPendingDelete] = useState<EmailTemplate | null>(null);

  async function remove(id: number) {
    setBusyId(id);
    await deleteJson(`/api/outreach/templates/${id}`);
    setBusyId(null);
    onChanged();
  }

  if (templates.length === 0) {
    return (
      <EmptyState
        icon={<FileText className="h-5 w-5" />}
        title="No templates yet"
        description="Create one above to start sending templated outreach emails."
      />
    );
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Subject</TableHead>
            <TableHead>Updated</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {templates.map((template) => (
            <TableRow key={template.id}>
              <TableCell className="font-medium text-slate-200">{template.name}</TableCell>
              <TableCell className="text-slate-400">{template.subject}</TableCell>
              <TableCell className="text-slate-500">{new Date(template.updated_at).toLocaleDateString()}</TableCell>
              <TableCell>
                <div className="flex items-center justify-end gap-1.5">
                  <Button variant="ghost" size="icon-sm" onClick={() => onEdit(template)} aria-label="Edit template">
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className="text-red-400 hover:text-red-300"
                    disabled={busyId === template.id}
                    onClick={() => setPendingDelete(template)}
                    aria-label="Delete template"
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
        title="Delete template"
        description={`Permanently delete "${pendingDelete?.name}"? This cannot be undone.`}
        confirmLabel="Delete"
        onConfirm={() => pendingDelete && remove(pendingDelete.id)}
      />
    </>
  );
}

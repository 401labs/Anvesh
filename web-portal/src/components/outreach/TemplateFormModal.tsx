'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { postJson, patchJson } from '@/lib/client';
import type { EmailTemplate, EmailTemplateCreate } from '@/lib/types';

const EMPTY: EmailTemplateCreate = {
  name: '',
  subject: '',
  body: '',
};

interface TemplateFormModalProps {
  /** When set, the modal is open in edit mode for this template. */
  editingTemplate?: EmailTemplate | null;
  /** When true, the modal is open in create mode. */
  createOpen?: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export function TemplateFormModal({ editingTemplate, createOpen, onClose, onSaved }: TemplateFormModalProps) {
  const [values, setValues] = useState<EmailTemplateCreate>(EMPTY);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const open = createOpen || editingTemplate != null;
  const isEdit = editingTemplate != null;

  useEffect(() => {
    if (editingTemplate) {
      setValues({
        name: editingTemplate.name,
        subject: editingTemplate.subject,
        body: editingTemplate.body,
      });
    } else if (createOpen) {
      setValues(EMPTY);
    }
    setError(null);
  }, [editingTemplate, createOpen]);

  function set<K extends keyof EmailTemplateCreate>(key: K, value: EmailTemplateCreate[K]) {
    setValues((v) => ({ ...v, [key]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!values.name.trim() || !values.subject.trim() || !values.body.trim()) {
      setError('Name, subject, and body are required.');
      return;
    }

    setSubmitting(true);
    const envelope = isEdit
      ? await patchJson(`/api/outreach/templates/${editingTemplate!.id}`, values)
      : await postJson('/api/outreach/templates', values);
    setSubmitting(false);

    if (!envelope.success) {
      setError(envelope.message);
      return;
    }

    onSaved();
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit template' : 'New template'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="max-h-[70vh] space-y-3 overflow-y-auto pr-1">
          <div>
            <Label className="mb-1.5 text-xs font-medium text-slate-400">Name</Label>
            <Input
              value={values.name}
              onChange={(e) => set('name', e.target.value)}
              className="bg-white/[0.03]"
            />
          </div>
          <div>
            <Label className="mb-1.5 text-xs font-medium text-slate-400">Subject</Label>
            <Input
              value={values.subject}
              onChange={(e) => set('subject', e.target.value)}
              className="bg-white/[0.03]"
            />
          </div>
          <div>
            <Label className="mb-1.5 text-xs font-medium text-slate-400">Body</Label>
            <Textarea
              value={values.body}
              onChange={(e) => set('body', e.target.value)}
              className="min-h-32 bg-white/[0.03]"
            />
            <p className="mt-1.5 text-xs text-slate-500">
              Use {'{{business_name}}'}, {'{{industry}}'}, {'{{location}}'}, {'{{address}}'}, {'{{category}}'} as
              placeholders.
            </p>
          </div>

          {error && <p className="text-xs text-red-400">{error}</p>}

          <Button type="submit" disabled={submitting}>
            {submitting ? 'Saving…' : isEdit ? 'Save changes' : 'Create template'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}

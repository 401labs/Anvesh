'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { usePolling } from '@/hooks/usePolling';
import { postJson } from '@/lib/client';
import type { EmailTemplatesResponse, SendEmailResult } from '@/lib/types';

const NO_TEMPLATE = '__none__';

interface SendEmailModalProps {
  leadIds: number[] | null;
  onClose: () => void;
  onSent: () => void;
}

export function SendEmailModal({ leadIds, onClose, onSent }: SendEmailModalProps) {
  const open = leadIds != null;
  const { data } = usePolling<EmailTemplatesResponse>(open ? '/api/outreach/templates' : null);

  const [templateId, setTemplateId] = useState<string>(NO_TEMPLATE);
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [skipped, setSkipped] = useState<number | null>(null);

  useEffect(() => {
    if (open) {
      setTemplateId(NO_TEMPLATE);
      setSubject('');
      setBody('');
      setError(null);
      setSkipped(null);
    }
  }, [open]);

  function selectTemplate(id: string | null) {
    if (id == null) return;
    setTemplateId(id);
    if (id === NO_TEMPLATE) {
      setSubject('');
      setBody('');
      return;
    }
    const template = data?.templates.find((t) => t.id.toString() === id);
    if (template) {
      setSubject(template.subject);
      setBody(template.body);
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!leadIds || leadIds.length === 0) return;
    if (!subject.trim() || !body.trim()) {
      setError('Subject and body are required.');
      return;
    }

    setSubmitting(true);
    const envelope = await postJson<SendEmailResult>('/api/outreach/email', {
      lead_ids: leadIds,
      subject,
      body,
    });
    setSubmitting(false);

    if (!envelope.success) {
      setError(envelope.message);
      return;
    }

    const skippedCount = (envelope.data?.skipped_no_email.length ?? 0) + (envelope.data?.skipped_no_lead.length ?? 0);
    if (skippedCount > 0) {
      setSkipped(skippedCount);
      onSent();
      return;
    }

    onSent();
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Send email{leadIds && leadIds.length > 1 ? ` to ${leadIds.length} leads` : ''}</DialogTitle>
        </DialogHeader>

        {skipped != null ? (
          <div className="space-y-4">
            <p className="text-sm text-slate-300">
              Sent. {skipped} lead{skipped === 1 ? '' : 's'} skipped — no email on file.
            </p>
            <Button onClick={onClose}>Done</Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="max-h-[70vh] space-y-3 overflow-y-auto pr-1">
            <div>
              <Label className="mb-1.5 text-xs font-medium text-slate-400">Template</Label>
              <Select value={templateId} onValueChange={selectTemplate}>
                <SelectTrigger className="w-full bg-white/[0.03]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NO_TEMPLATE}>No template (write one-off)</SelectItem>
                  {data?.templates.map((t) => (
                    <SelectItem key={t.id} value={t.id.toString()}>
                      {t.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="mb-1.5 text-xs font-medium text-slate-400">Subject</Label>
              <Input value={subject} onChange={(e) => setSubject(e.target.value)} className="bg-white/[0.03]" />
            </div>
            <div>
              <Label className="mb-1.5 text-xs font-medium text-slate-400">Body</Label>
              <Textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                className="min-h-32 bg-white/[0.03]"
              />
            </div>

            {error && <p className="text-xs text-red-400">{error}</p>}

            <Button type="submit" disabled={submitting || !leadIds || leadIds.length === 0}>
              {submitting ? 'Sending…' : 'Send'}
            </Button>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}

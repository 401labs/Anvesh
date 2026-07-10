'use client';

import { useState } from 'react';
import { Plus, Inbox } from 'lucide-react';
import { usePolling } from '@/hooks/usePolling';
import { Button } from '@/components/ui/button';
import { ErrorBanner } from '@/components/shared/ErrorBanner';
import { TemplateTable } from '@/components/outreach/TemplateTable';
import { TemplateFormModal } from '@/components/outreach/TemplateFormModal';
import { postJson } from '@/lib/client';
import type { EmailTemplate, EmailTemplatesResponse } from '@/lib/types';

export default function OutreachPage() {
  const { data, message, loading, unreachable, refetch } = usePolling<EmailTemplatesResponse>('/api/outreach/templates');
  const [createOpen, setCreateOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<EmailTemplate | null>(null);
  const [checkingReplies, setCheckingReplies] = useState(false);
  const [replyResult, setReplyResult] = useState<string | null>(null);

  async function checkReplies() {
    setCheckingReplies(true);
    setReplyResult(null);
    const envelope = await postJson<{ matched: number }>('/api/outreach/check-replies');
    setCheckingReplies(false);
    if (envelope.success && envelope.data) {
      setReplyResult(
        envelope.data.matched === 0
          ? 'No new replies.'
          : `${envelope.data.matched} repl${envelope.data.matched === 1 ? 'y' : 'ies'} matched — lead status updated.`
      );
    } else {
      setReplyResult(envelope.message);
    }
  }

  return (
    <div className="w-full px-6 py-8 md:px-10">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-white">Outreach</h1>
          <p className="mt-1 text-sm text-slate-500">Manage email templates used to reach out to leads.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" disabled={checkingReplies} onClick={checkReplies}>
            <Inbox className="h-3.5 w-3.5" />
            {checkingReplies ? 'Checking…' : 'Check for replies'}
          </Button>
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="h-3.5 w-3.5" />
            New template
          </Button>
        </div>
      </div>

      {replyResult && <p className="mb-4 text-xs text-slate-500">{replyResult}</p>}

      {unreachable && <ErrorBanner message={message ?? undefined} />}

      {!unreachable && !loading && !data && <ErrorBanner message={message ?? 'Could not load templates.'} />}
      {data && <TemplateTable templates={data.templates} onChanged={refetch} onEdit={setEditingTemplate} />}

      <TemplateFormModal createOpen={createOpen} onClose={() => setCreateOpen(false)} onSaved={refetch} />
      <TemplateFormModal editingTemplate={editingTemplate} onClose={() => setEditingTemplate(null)} onSaved={refetch} />
    </div>
  );
}

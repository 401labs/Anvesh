'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { usePolling } from '@/hooks/usePolling';
import { toneClass, type Tone } from '@/lib/status';
import type { OutreachLogsPage } from '@/lib/types';

const STATUS_TONE: Record<string, Tone> = {
  sent: 'emerald',
  failed: 'red',
  pending: 'amber',
  queued: 'indigo',
};

interface OutreachHistoryDrawerProps {
  leadId: number | null;
  onClose: () => void;
}

export function OutreachHistoryDrawer({ leadId, onClose }: OutreachHistoryDrawerProps) {
  const { data, message, loading } = usePolling<OutreachLogsPage>(
    leadId != null ? `/api/outreach/logs?lead_id=${leadId}` : null
  );

  return (
    <Dialog open={leadId != null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Outreach history</DialogTitle>
        </DialogHeader>
        {loading && <p className="text-sm text-slate-500">Loading…</p>}
        {!loading && !data && <p className="text-sm text-red-400">{message ?? 'Could not load outreach history.'}</p>}
        {data && data.logs.length === 0 && <p className="text-sm text-slate-500">No outreach sent to this lead yet.</p>}
        {data && data.logs.length > 0 && (
          <ul className="max-h-[60vh] space-y-2 overflow-y-auto pr-1">
            {data.logs.map((log) => (
              <li key={log.id} className="rounded-xl border border-white/10 bg-white/[0.02] px-3.5 py-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className={toneClass('slate')}>
                      Email
                    </Badge>
                    <Badge variant="outline" className={toneClass(STATUS_TONE[log.status] ?? 'slate')}>
                      {log.status}
                    </Badge>
                  </div>
                  <span className="text-xs text-slate-500">{log.created_at}</span>
                </div>
                {log.subject && <p className="mt-2 text-sm text-slate-200">{log.subject}</p>}
                {log.error && <p className="mt-1 text-xs text-red-400">{log.error}</p>}
              </li>
            ))}
          </ul>
        )}
      </DialogContent>
    </Dialog>
  );
}

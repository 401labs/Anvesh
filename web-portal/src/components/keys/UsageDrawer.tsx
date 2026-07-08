'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { usePolling } from '@/hooks/usePolling';
import type { UsageStats } from '@/lib/types';

interface UsageDrawerProps {
  keyId: number | null;
  onClose: () => void;
}

export function UsageDrawer({ keyId, onClose }: UsageDrawerProps) {
  const { data, message, loading } = usePolling<UsageStats>(keyId != null ? `/api/keys/${keyId}/usage` : null);

  return (
    <Dialog open={keyId != null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Usage stats</DialogTitle>
        </DialogHeader>
        {loading && <p className="text-sm text-slate-500">Loading…</p>}
        {!loading && !data && <p className="text-sm text-red-400">{message ?? 'Could not load usage.'}</p>}
        {data && (
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-xs uppercase tracking-wider text-slate-500">Total requests</dt>
              <dd className="mt-1 text-lg font-semibold text-white">{data.total_requests}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wider text-slate-500">Total leads</dt>
              <dd className="mt-1 text-lg font-semibold text-white">{data.total_leads}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wider text-slate-500">This month</dt>
              <dd className="mt-1 text-lg font-semibold text-white">{data.monthly_leads}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wider text-slate-500">Remaining quota</dt>
              <dd className="mt-1 text-lg font-semibold text-white">{data.remaining_quota}</dd>
            </div>
          </dl>
        )}
      </DialogContent>
    </Dialog>
  );
}

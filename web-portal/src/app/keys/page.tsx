'use client';

import { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { usePolling } from '@/hooks/usePolling';
import { Button } from '@/components/ui/button';
import { ErrorBanner } from '@/components/shared/ErrorBanner';
import { NewKeyForm } from '@/components/keys/NewKeyForm';
import { KeyTable } from '@/components/keys/KeyTable';
import { UsageDrawer } from '@/components/keys/UsageDrawer';
import { EditKeyModal } from '@/components/keys/EditKeyModal';
import type { ApiKey, ApiKeysPage } from '@/lib/types';

const PAGE_SIZE = 20;

export default function KeysPage() {
  const [page, setPage] = useState(0);
  const {
    data,
    message,
    loading,
    unreachable,
    refetch,
  } = usePolling<ApiKeysPage>(`/api/keys?limit=${PAGE_SIZE}&offset=${page * PAGE_SIZE}`);
  const [usageKeyId, setUsageKeyId] = useState<number | null>(null);
  const [editingKey, setEditingKey] = useState<ApiKey | null>(null);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="w-full px-6 py-8 md:px-10">
      <div className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight text-white">API Keys</h1>
        <p className="mt-1 text-sm text-slate-500">
          {data ? `${data.total} key${data.total === 1 ? '' : 's'}. ` : ''}Create, edit, revoke, and monitor usage.
        </p>
      </div>

      {unreachable && <ErrorBanner message={message ?? undefined} />}

      <div className="mb-6">
        <NewKeyForm onCreated={refetch} />
      </div>

      {!unreachable && !loading && !data && <ErrorBanner message={message ?? 'Could not load API keys.'} />}
      {data && <KeyTable keys={data.keys} onChanged={refetch} onViewUsage={setUsageKeyId} onEdit={setEditingKey} />}

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

      <UsageDrawer keyId={usageKeyId} onClose={() => setUsageKeyId(null)} />
      <EditKeyModal apiKey={editingKey} onClose={() => setEditingKey(null)} onSaved={refetch} />
    </div>
  );
}

'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { apiRequest } from '@/lib/client';

interface UsePollingResult<T> {
  data: T | null;
  message: string | null;
  loading: boolean;
  unreachable: boolean;
  refetch: () => void;
}

/** Fetches `url` once, and again every `intervalMs` if given (null = one-shot). Pass `url` as null to skip fetching entirely. */
export function usePolling<T>(url: string | null, intervalMs: number | null = null): UsePollingResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(url != null);
  const [unreachable, setUnreachable] = useState(false);

  const fetchOnce = useCallback(async () => {
    if (!url) return;
    const envelope = await apiRequest<T>(url);
    setUnreachable(envelope.code === 'unreachable' || envelope.code === 'config');
    if (envelope.success) {
      setData(envelope.data);
      setMessage(null);
    } else {
      setMessage(envelope.message);
    }
    setLoading(false);
  }, [url]);

  const fetchOnceRef = useRef(fetchOnce);
  fetchOnceRef.current = fetchOnce;

  useEffect(() => {
    if (!url) {
      setData(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    fetchOnceRef.current();
    if (!intervalMs) return;
    const timer = setInterval(() => fetchOnceRef.current(), intervalMs);
    return () => clearInterval(timer);
  }, [url, intervalMs]);

  return { data, message, loading, unreachable, refetch: fetchOnce };
}

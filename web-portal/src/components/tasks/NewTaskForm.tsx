'use client';

import { useState, type FormEvent } from 'react';
import { Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { LocationsInput } from '@/components/tasks/LocationsInput';
import { postJson } from '@/lib/client';
import type { TaskConfig } from '@/lib/types';

interface NewTaskFormProps {
  onStarted: () => void;
}

export function NewTaskForm({ onStarted }: NewTaskFormProps) {
  const [industry, setIndustry] = useState('');
  const [locations, setLocations] = useState<string[]>([]);
  const [unlimited, setUnlimited] = useState(true);
  const [limit, setLimit] = useState(50);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!industry.trim() || locations.length === 0) {
      setError('Industry and at least one location are required.');
      return;
    }

    setSubmitting(true);
    const body: TaskConfig = {
      industry: industry.trim(),
      locations,
      limit_per_location: unlimited ? -1 : limit,
    };
    const envelope = await postJson('/api/tasks', body);
    setSubmitting(false);

    if (!envelope.success) {
      setError(envelope.message);
      return;
    }

    setIndustry('');
    setLocations([]);
    onStarted();
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 border-b border-white/10 pb-6">
      <h2 className="text-sm font-semibold text-white">Start a new scrape</h2>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <Label className="mb-1.5 text-xs font-medium text-slate-400">Industry</Label>
          <Input
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            placeholder="restaurants"
            className="bg-white/[0.03]"
          />
        </div>

        <div>
          <Label className="mb-1.5 text-xs font-medium text-slate-400">Locations (press Enter to add each one)</Label>
          <LocationsInput value={locations} onChange={setLocations} placeholder="Mumbai, Delhi, Bangalore…" />
        </div>
      </div>

      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2 text-xs text-slate-400">
          <Checkbox checked={unlimited} onCheckedChange={(c) => setUnlimited(c === true)} />
          Unlimited leads per location
        </label>
        {!unlimited && (
          <Input
            type="number"
            min={1}
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="w-24 bg-white/[0.03]"
          />
        )}
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      <Button type="submit" disabled={submitting}>
        <Play className="h-3.5 w-3.5" />
        {submitting ? 'Starting…' : 'Start task'}
      </Button>
    </form>
  );
}

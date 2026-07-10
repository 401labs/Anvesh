'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { LocationsInput } from '@/components/tasks/LocationsInput';
import { postJson, patchJson } from '@/lib/client';
import type { Schedule, ScheduleCreate } from '@/lib/types';

const INTERVAL_OPTIONS = [
  { value: '24', label: 'Daily' },
  { value: '168', label: 'Weekly' },
  { value: '720', label: 'Monthly (30d)' },
];

const EMPTY: ScheduleCreate = {
  name: '',
  industry: '',
  locations: [],
  limit_per_location: -1,
  interval_hours: 24,
};

interface ScheduleFormModalProps {
  /** When set, the modal is open in edit mode for this schedule. */
  editingSchedule?: Schedule | null;
  /** When true, the modal is open in create mode. */
  createOpen?: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export function ScheduleFormModal({ editingSchedule, createOpen, onClose, onSaved }: ScheduleFormModalProps) {
  const [values, setValues] = useState<ScheduleCreate>(EMPTY);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const open = createOpen || editingSchedule != null;
  const isEdit = editingSchedule != null;

  useEffect(() => {
    if (editingSchedule) {
      setValues({
        name: editingSchedule.name,
        industry: editingSchedule.industry,
        locations: editingSchedule.locations,
        limit_per_location: editingSchedule.limit_per_location,
        interval_hours: editingSchedule.interval_hours,
      });
    } else if (createOpen) {
      setValues(EMPTY);
    }
    setError(null);
  }, [editingSchedule, createOpen]);

  function set<K extends keyof ScheduleCreate>(key: K, value: ScheduleCreate[K]) {
    setValues((v) => ({ ...v, [key]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!values.name.trim() || !values.industry.trim() || values.locations.length === 0) {
      setError('Name, industry, and at least one location are required.');
      return;
    }

    setSubmitting(true);
    const envelope = isEdit
      ? await patchJson(`/api/schedules/${editingSchedule!.id}`, values)
      : await postJson('/api/schedules', values);
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
          <DialogTitle>{isEdit ? 'Edit schedule' : 'New schedule'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <Label className="mb-1.5 text-xs font-medium text-slate-400">Name</Label>
            <Input
              value={values.name}
              onChange={(e) => set('name', e.target.value)}
              placeholder="Weekly Mumbai restaurants"
              className="bg-white/[0.03]"
            />
          </div>
          <div>
            <Label className="mb-1.5 text-xs font-medium text-slate-400">Industry</Label>
            <Input
              value={values.industry}
              onChange={(e) => set('industry', e.target.value)}
              placeholder="restaurants"
              className="bg-white/[0.03]"
            />
          </div>
          <div>
            <Label className="mb-1.5 text-xs font-medium text-slate-400">
              Locations (press Enter to add each one)
            </Label>
            <LocationsInput
              value={values.locations}
              onChange={(v) => set('locations', v)}
              placeholder="Mumbai, Delhi, Bangalore…"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="mb-1.5 text-xs font-medium text-slate-400">Limit per location</Label>
              <Input
                type="number"
                min={-1}
                value={values.limit_per_location}
                onChange={(e) => set('limit_per_location', Number(e.target.value))}
                className="bg-white/[0.03]"
              />
              <p className="mt-1 text-[11px] text-slate-600">-1 for unlimited</p>
            </div>
            <div>
              <Label className="mb-1.5 text-xs font-medium text-slate-400">Repeats</Label>
              <Select
                value={String(values.interval_hours)}
                onValueChange={(v) => set('interval_hours', Number(v))}
              >
                <SelectTrigger className="w-full bg-white/[0.03]">
                  <SelectValue>
                    {INTERVAL_OPTIONS.find((o) => o.value === String(values.interval_hours))?.label ??
                      `Every ${values.interval_hours}h`}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {INTERVAL_OPTIONS.map((o) => (
                    <SelectItem key={o.value} value={o.value}>
                      {o.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {error && <p className="text-xs text-red-400">{error}</p>}

          <Button type="submit" disabled={submitting}>
            {submitting ? 'Saving…' : isEdit ? 'Save changes' : 'Create schedule'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}

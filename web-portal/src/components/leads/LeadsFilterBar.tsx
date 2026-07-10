'use client';

import { Filter, ArrowUpDown, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from '@/components/ui/dropdown-menu';
import { usePolling } from '@/hooks/usePolling';
import type { LeadFilterOptions, LeadFilters, LeadSortBy, LeadStatus, SortDir } from '@/lib/types';

const ANY = '__any__';

const STATUS_OPTIONS: LeadStatus[] = ['new', 'contacted', 'replied', 'interested', 'won', 'lost'];

const SORT_OPTIONS: { value: string; label: string; sort_by: LeadSortBy; sort_dir: SortDir }[] = [
  { value: 'score_desc', label: 'Best prospects first', sort_by: 'score', sort_dir: 'desc' },
  { value: 'score_asc', label: 'Worst prospects first', sort_by: 'score', sort_dir: 'asc' },
  { value: 'newest', label: 'Newest first', sort_by: 'created_at', sort_dir: 'desc' },
  { value: 'oldest', label: 'Oldest first', sort_by: 'created_at', sort_dir: 'asc' },
  { value: 'rating_desc', label: 'Highest rated', sort_by: 'rating', sort_dir: 'desc' },
  { value: 'rating_asc', label: 'Lowest rated', sort_by: 'rating', sort_dir: 'asc' },
  { value: 'reviews_desc', label: 'Most reviews', sort_by: 'review_count', sort_dir: 'desc' },
  { value: 'reviews_asc', label: 'Fewest reviews', sort_by: 'review_count', sort_dir: 'asc' },
  { value: 'name_asc', label: 'Name A–Z', sort_by: 'business_name', sort_dir: 'asc' },
  { value: 'name_desc', label: 'Name Z–A', sort_by: 'business_name', sort_dir: 'desc' },
];

interface LeadsFilterBarProps {
  filters: LeadFilters;
  onChange: (filters: LeadFilters) => void;
}

interface Chip {
  key: keyof LeadFilters;
  label: string;
}

function buildActiveChips(filters: LeadFilters): Chip[] {
  const chips: Chip[] = [];
  if (filters.industry) chips.push({ key: 'industry', label: `Industry: ${filters.industry}` });
  if (filters.location) chips.push({ key: 'location', label: `Location: ${filters.location}` });
  if (filters.category) chips.push({ key: 'category', label: `Category: ${filters.category}` });
  if (filters.has_website !== undefined) {
    chips.push({ key: 'has_website', label: filters.has_website ? 'Has website' : 'No website' });
  }
  if (filters.has_email !== undefined) {
    chips.push({ key: 'has_email', label: filters.has_email ? 'Has email' : 'No email' });
  }
  if (filters.is_claimed !== undefined) {
    chips.push({ key: 'is_claimed', label: filters.is_claimed ? 'Claimed' : 'Unclaimed' });
  }
  if (filters.min_rating !== undefined) chips.push({ key: 'min_rating', label: `${filters.min_rating}+ stars` });
  if (filters.min_score !== undefined) chips.push({ key: 'min_score', label: `Score ${filters.min_score}+` });
  if (filters.status) chips.push({ key: 'status', label: `Status: ${filters.status}` });
  return chips;
}

export function LeadsFilterBar({ filters, onChange }: LeadsFilterBarProps) {
  const { data: options } = usePolling<LeadFilterOptions>('/api/leads/filter-options');

  function set<K extends keyof LeadFilters>(key: K, value: LeadFilters[K]) {
    onChange({ ...filters, [key]: value });
  }

  function clearOne(key: keyof LeadFilters) {
    const next = { ...filters };
    delete next[key];
    onChange(next);
  }

  function clearAllFilters() {
    onChange({ search: filters.search, sort_by: filters.sort_by, sort_dir: filters.sort_dir });
  }

  const activeChips = buildActiveChips(filters);
  const currentSort =
    SORT_OPTIONS.find(
      (o) => o.sort_by === (filters.sort_by ?? 'created_at') && o.sort_dir === (filters.sort_dir ?? 'desc')
    ) ?? SORT_OPTIONS[0];

  return (
    <div className="mb-6 space-y-3 border-b border-white/10 pb-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-1 items-center gap-2">
          <Input
            placeholder="Search name, address, phone…"
            value={filters.search ?? ''}
            onChange={(e) => set('search', e.target.value || undefined)}
            className="w-56 bg-white/[0.03]"
          />

          <Popover>
            <PopoverTrigger render={<Button variant="secondary" size="sm" />}>
              <Filter className="h-3.5 w-3.5" />
              Filters
              {activeChips.length > 0 && (
                <Badge className="ml-0.5 h-4 min-w-4 justify-center rounded-full bg-indigo-500 px-1 text-[10px] text-white">
                  {activeChips.length}
                </Badge>
              )}
            </PopoverTrigger>
            <PopoverContent align="start" className="w-80">
              <div className="space-y-3">
                <FilterSelect
                  label="Industry"
                  value={filters.industry}
                  onChange={(v) => set('industry', v)}
                  options={options?.industries ?? []}
                />
                <FilterSelect
                  label="Location"
                  value={filters.location}
                  onChange={(v) => set('location', v)}
                  options={options?.locations ?? []}
                />
                <FilterSelect
                  label="Category"
                  value={filters.category}
                  onChange={(v) => set('category', v)}
                  options={options?.categories ?? []}
                />
                <div className="grid grid-cols-2 gap-2">
                  <TriStateSelect label="Website" value={filters.has_website} onChange={(v) => set('has_website', v)} />
                  <TriStateSelect label="Email" value={filters.has_email} onChange={(v) => set('has_email', v)} />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <TriStateSelect
                    label="Claim status"
                    value={filters.is_claimed}
                    onChange={(v) => set('is_claimed', v)}
                    trueLabel="Claimed"
                    falseLabel="Unclaimed"
                  />
                  <div>
                    <label className="mb-1 block text-xs text-slate-500">Min rating</label>
                    <Select
                      value={filters.min_rating?.toString() ?? ANY}
                      onValueChange={(v) => set('min_rating', !v || v === ANY ? undefined : Number(v))}
                    >
                      <SelectTrigger className="w-full bg-white/[0.03]">
                        <SelectValue>{filters.min_rating != null ? `${filters.min_rating}+` : 'Any'}</SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value={ANY}>Any rating</SelectItem>
                        <SelectItem value="3">3+ stars</SelectItem>
                        <SelectItem value="4">4+ stars</SelectItem>
                        <SelectItem value="4.5">4.5+ stars</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="mb-1 block text-xs text-slate-500">Status</label>
                    <Select
                      value={filters.status ?? ANY}
                      onValueChange={(v) => set('status', !v || v === ANY ? undefined : (v as LeadStatus))}
                    >
                      <SelectTrigger className="w-full bg-white/[0.03]">
                        <SelectValue>
                          {filters.status
                            ? filters.status.charAt(0).toUpperCase() + filters.status.slice(1)
                            : 'Any status'}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value={ANY}>Any status</SelectItem>
                        {STATUS_OPTIONS.map((s) => (
                          <SelectItem key={s} value={s}>
                            {s.charAt(0).toUpperCase() + s.slice(1)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-slate-500">Min score</label>
                    <Select
                      value={filters.min_score?.toString() ?? ANY}
                      onValueChange={(v) => set('min_score', !v || v === ANY ? undefined : Number(v))}
                    >
                      <SelectTrigger className="w-full bg-white/[0.03]">
                        <SelectValue>{filters.min_score != null ? `${filters.min_score}+` : 'Any'}</SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value={ANY}>Any score</SelectItem>
                        <SelectItem value="30">30+</SelectItem>
                        <SelectItem value="50">50+</SelectItem>
                        <SelectItem value="70">70+</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {activeChips.length > 0 && (
                  <Button variant="ghost" size="sm" className="w-full" onClick={clearAllFilters}>
                    Clear all filters
                  </Button>
                )}
              </div>
            </PopoverContent>
          </Popover>
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger render={<Button variant="secondary" size="sm" />}>
            <ArrowUpDown className="h-3.5 w-3.5" />
            {currentSort.label}
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuRadioGroup
              value={currentSort.value}
              onValueChange={(key) => {
                const opt = SORT_OPTIONS.find((o) => o.value === key);
                if (opt) onChange({ ...filters, sort_by: opt.sort_by, sort_dir: opt.sort_dir });
              }}
            >
              {SORT_OPTIONS.map((o) => (
                <DropdownMenuRadioItem key={o.value} value={o.value}>
                  {o.label}
                </DropdownMenuRadioItem>
              ))}
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {activeChips.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          {activeChips.map((chip) => (
            <Badge
              key={chip.key}
              variant="outline"
              className="gap-1 border-white/10 bg-white/[0.04] py-1 pr-1 pl-2.5 text-slate-300"
            >
              {chip.label}
              <button
                type="button"
                onClick={() => clearOne(chip.key)}
                className="rounded-full p-0.5 hover:bg-white/10"
                aria-label={`Remove ${chip.label} filter`}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value?: string;
  onChange: (v: string | undefined) => void;
  options: string[];
}) {
  return (
    <div>
      <label className="mb-1 block text-xs text-slate-500">{label}</label>
      <Select value={value ?? ANY} onValueChange={(v) => onChange(!v || v === ANY ? undefined : v)}>
        <SelectTrigger className="w-full bg-white/[0.03]">
          <SelectValue>{value ?? `All ${label.toLowerCase()}`}</SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ANY}>All {label.toLowerCase()}</SelectItem>
          {options.map((opt) => (
            <SelectItem key={opt} value={opt}>
              {opt}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function TriStateSelect({
  label,
  value,
  onChange,
  trueLabel = 'Yes',
  falseLabel = 'No',
}: {
  label: string;
  value?: boolean;
  onChange: (v: boolean | undefined) => void;
  trueLabel?: string;
  falseLabel?: string;
}) {
  const current = value === undefined ? ANY : value ? 'true' : 'false';
  const displayText = value === undefined ? 'Any' : value ? trueLabel : falseLabel;
  return (
    <div>
      <label className="mb-1 block text-xs text-slate-500">{label}</label>
      <Select value={current} onValueChange={(v) => onChange(!v || v === ANY ? undefined : v === 'true')}>
        <SelectTrigger className="w-full bg-white/[0.03]">
          <SelectValue>{displayText}</SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ANY}>Any</SelectItem>
          <SelectItem value="true">{trueLabel}</SelectItem>
          <SelectItem value="false">{falseLabel}</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}

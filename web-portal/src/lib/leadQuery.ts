import type { LeadFilters } from './types';

/** Turns a LeadFilters object into a query string (no leading `?`), omitting unset fields. */
export function leadFiltersToQuery(filters: LeadFilters): string {
  const params = new URLSearchParams();
  if (filters.industry) params.set('industry', filters.industry);
  if (filters.location) params.set('location', filters.location);
  if (filters.category) params.set('category', filters.category);
  if (filters.has_website !== undefined) params.set('has_website', String(filters.has_website));
  if (filters.has_email !== undefined) params.set('has_email', String(filters.has_email));
  if (filters.is_claimed !== undefined) params.set('is_claimed', String(filters.is_claimed));
  if (filters.min_rating !== undefined) params.set('min_rating', String(filters.min_rating));
  if (filters.min_score !== undefined) params.set('min_score', String(filters.min_score));
  if (filters.status) params.set('status', filters.status);
  if (filters.search) params.set('search', filters.search);
  if (filters.sort_by) params.set('sort_by', filters.sort_by);
  if (filters.sort_dir) params.set('sort_dir', filters.sort_dir);
  return params.toString();
}

export const EMPTY_LEAD_FILTERS: LeadFilters = {};

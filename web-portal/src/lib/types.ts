// Types mirroring automation-server's app/helpers/response.py envelope and
// app/models/*.py schemas. Keep these in sync if the backend models change.

export interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T | null;
  error: boolean;
  /** Set only by this portal's own /api proxy layer on infra failures, never by automation-server itself. */
  code?: 'unreachable' | 'config';
}

export type TaskStatus = 'idle' | 'running' | 'completed' | 'stopped' | 'error';

export interface TaskConfig {
  industry: string;
  locations: string[];
  limit_per_location: number;
  headless: boolean;
}

export interface Task {
  id: string;
  config: TaskConfig;
  running: boolean;
  stop: boolean;
  status: TaskStatus;
  error: string | null;
  created_at?: string;
}

export interface TasksPage {
  tasks: Task[];
  total: number;
  limit: number;
  offset: number;
}

export interface Lead {
  id: number;
  business_name: string;
  industry: string;
  category: string | null;
  location: string;
  address: string;
  rating: number | null;
  review_count: number | null;
  is_claimed: boolean | null;
  has_website: boolean;
  website_url: string | null;
  phone: string | null;
  email: string | null;
  status: LeadStatus;
  maps_url: string | null;
  score: number;
  created_at: string;
}

export interface LeadsPage {
  leads: Lead[];
  total: number;
  limit: number;
  offset: number;
}

export interface LeadFilterOptions {
  industries: string[];
  locations: string[];
  categories: string[];
}

export type LeadSortBy = 'created_at' | 'rating' | 'review_count' | 'business_name' | 'score';
export type SortDir = 'asc' | 'desc';

export interface LeadFilters {
  industry?: string;
  location?: string;
  category?: string;
  has_website?: boolean;
  has_email?: boolean;
  is_claimed?: boolean;
  min_rating?: number;
  min_score?: number;
  status?: LeadStatus;
  search?: string;
  sort_by?: LeadSortBy;
  sort_dir?: SortDir;
}

export interface LeadCreate {
  business_name: string;
  industry: string;
  location: string;
  address: string;
  category?: string;
  rating?: number;
  review_count?: number;
  is_claimed?: boolean;
  has_website?: boolean;
  website_url?: string;
  phone?: string;
  email?: string;
  status?: LeadStatus;
  maps_url?: string;
}

export type LeadUpdate = Partial<LeadCreate>;

export type ApiKeyTier = 'free' | 'pro' | 'enterprise';

export interface ApiKey {
  id: number;
  name: string;
  key_prefix: string;
  tier: ApiKeyTier;
  monthly_limit: number;
  is_active: boolean;
  created_at: string;
  expires_at: string | null;
}

export interface ApiKeysPage {
  keys: ApiKey[];
  total: number;
  limit: number;
  offset: number;
}

export interface ApiKeyUpdate {
  name?: string;
  tier?: ApiKeyTier;
  expires_in_days?: number;
  clear_expiry?: boolean;
}

export interface ApiKeyCreated extends Omit<ApiKey, 'is_active'> {
  /** Only ever present in the response to the create call, never persisted. */
  key: string;
}

export interface UsageStats {
  api_key_id: number;
  total_requests: number;
  total_leads: number;
  monthly_leads: number;
  monthly_limit: number;
  remaining_quota: string | number;
}

export interface AutomationStats {
  timestamp: string;
  tasks: {
    total: number;
    running: number;
    completed: number;
    stopped: number;
    error: number;
  };
  active_scraping: {
    industries: string[];
    locations: string[];
  };
  success_rate: string;
}

export type LeadStatus = 'new' | 'contacted' | 'replied' | 'interested' | 'won' | 'lost';

export interface EmailTemplate {
  id: number;
  name: string;
  subject: string;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface EmailTemplateCreate {
  name: string;
  subject: string;
  body: string;
}

export type EmailTemplateUpdate = Partial<EmailTemplateCreate>;

export interface EmailTemplatesResponse {
  templates: EmailTemplate[];
}

export type OutreachChannel = 'email';

export interface OutreachLog {
  id: number;
  lead_id: number;
  channel: OutreachChannel;
  status: string;
  subject: string | null;
  body: string | null;
  error: string | null;
  created_at: string;
}

export interface OutreachLogsPage {
  logs: OutreachLog[];
  total: number;
  limit: number;
  offset: number;
}

export interface SendEmailRequest {
  lead_ids: number[];
  template_id?: number;
  subject?: string;
  body?: string;
}

export interface SendEmailResult {
  result?: { lead_id: number; sent: boolean; error: string | null };
  queued?: number;
  skipped_no_lead: number[];
  skipped_no_email: number[];
}

export interface DashboardStats {
  leads: {
    total: number;
    by_status: Record<LeadStatus, number>;
    by_score_tier: { hot: number; warm: number; cool: number };
    with_email: number;
    with_website: number;
    unclaimed: number;
  };
  leads_by_day: { date: string; count: number }[];
  top_industries: { industry: string; count: number }[];
  top_locations: { location: string; count: number }[];
  outreach: {
    total: number;
    sent: number;
    failed: number;
  };
  tasks: {
    total: number;
    running: number;
    completed: number;
    stopped: number;
    error: number;
  };
}

export interface Schedule {
  id: number;
  name: string;
  industry: string;
  locations: string[];
  limit_per_location: number;
  interval_hours: number;
  enabled: boolean;
  last_run_at: string | null;
  next_run_at: string;
  created_at: string;
}

export interface ScheduleCreate {
  name: string;
  industry: string;
  locations: string[];
  limit_per_location: number;
  interval_hours: number;
}

export type ScheduleUpdate = Partial<ScheduleCreate> & { enabled?: boolean };

export interface SchedulesResponse {
  schedules: Schedule[];
}

export interface EmailConfig {
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_from_name: string;
  imap_host: string;
  imap_port: number;
  smtp_app_password_set: boolean;
}

export interface EmailConfigUpdate {
  smtp_host?: string;
  smtp_port?: number;
  smtp_user?: string;
  smtp_app_password?: string;
  smtp_from_name?: string;
  imap_host?: string;
  imap_port?: number;
}

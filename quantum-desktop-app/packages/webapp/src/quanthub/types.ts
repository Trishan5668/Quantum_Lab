/** Shared QuantHub API types (mirrors app/quanthub/router.py). */

export type Visibility = "public" | "private";

/** Identity mechanisms the API reports as available (see `GET /me`). */
export interface IdentityCapabilities {
  local_sessions: boolean;
  firebase: boolean;
}

export interface Viewer {
  id: string;
  handle: string;
  display_name: string;
  email: string | null;
  authenticated: boolean;
  mode: "authenticated" | "guest" | "local";
  capabilities?: IdentityCapabilities;
  profile?: {
    id: string;
    handle: string;
    display_name: string;
    email: string | null;
    created_at: string;
  } | null;
  project_count?: number;
}

export interface ProjectSummary {
  id: string;
  name: string;
  slug: string;
  full_name: string;
  owner: { handle: string; display_name: string };
  description: string;
  visibility: Visibility;
  topics: string[];
  language: string | null;
  license: string | null;
  updated_at: string;
  revision: string | null;
  stars: number;
  kinds?: string[];
}

export interface ProjectList {
  items: ProjectSummary[];
  page: number;
  per_page: number;
  total: number;
  has_more: boolean;
}

export interface LanguageSpec {
  id: string;
  label: string;
  extensions: string[];
  filenames: string[];
  mode: string | null;
  highlight: boolean;
  editable: boolean;
  execution: {
    supported: boolean;
    runtime: string | null;
    sandboxed: boolean;
    enabled_by_default: boolean;
    notes: string;
  };
  category: string;
}

export interface TreeEntry {
  name: string;
  path: string;
  type: "blob" | "tree";
  sha: string;
  size: number | null;
  language?: string;
  label?: string;
}

export interface TreePayload {
  revision: string | null;
  path: string;
  entries: TreeEntry[];
  parent: string | null;
}

export interface CommitInfo {
  sha: string;
  short_sha?: string;
  message: string;
  author_name: string;
  authored_at: string;
  parents?: string[];
  files?: number | null;
}

export interface BlobPayload {
  path: string;
  revision: string;
  size: number;
  language: LanguageSpec;
  binary: boolean;
  too_large: boolean;
  truncated?: boolean;
  content: string | null;
  editable?: boolean;
  last_commit?: { sha: string; message: string; author_name: string; authored_at: string } | null;
  message?: string;
}

export interface ReadmePayload {
  path: string;
  content: string | null;
  too_large: boolean;
}

export interface ActivityEvent {
  id: number;
  type: string;
  actor: string;
  payload: Record<string, unknown>;
  created_at: string;
  project?: { full_name: string; name: string };
  project_id?: string;
}

export interface ProjectDetail extends ProjectSummary {
  website: string | null;
  default_branch: string;
  readme_path: string | null;
  created_at: string;
  archived: boolean;
  archived_at: string | null;
  file_count: number;
  commit_count: number;
  latest_commit: CommitInfo | null;
  watchers: number;
  experiment_count: number;
  run_count: number;
  viewer: {
    role: "owner" | "maintainer" | "reader" | null;
    can_write: boolean;
    can_admin: boolean;
    starred: boolean;
    watched: boolean;
  };
  readme: ReadmePayload | null;
  tree: TreePayload;
  recent_commits: CommitInfo[];
  experiments: ExperimentSpec[];
  runs: RunSummary[];
}

export interface NewsItem {
  id: string;
  title: string;
  summary: string;
  source: string;
  url: string;
  published_at: string | null;
  tags: string[];
  category: string;
  kind: string;
  verified_at: string | null;
  verification: string | null;
  related: string[];
  live: boolean;
}

export interface NewsFeed {
  items: NewsItem[];
  feed: {
    kind: string;
    label: string;
    live: boolean;
    fetched_at: string | null;
    warning: string | null;
    ttl_seconds: number;
  };
  attribution: string;
}

export interface ExperimentSpec {
  id: string;
  project_id: string;
  slug: string;
  name: string;
  description: string;
  protocol: Record<string, unknown>;
  config_hash: string | null;
  created_at: string;
  updated_at: string;
  created_by: string;
  run_count: number;
  last_run_at: string | null;
  last_status: string | null;
}

export type RunStatus =
  | "queued"
  | "running"
  | "cancelling"
  | "completed"
  | "failed"
  | "cancelled";

export interface DecoderResult {
  decoder: string;
  trials: number | null;
  operational_failures: number | null;
  logical_failures: number | null;
  probability: number | null;
  interval_low: number | null;
  interval_high: number | null;
  method: string | null;
  confidence_level: number | null;
  zero_failure_upper_bound: number | null;
  status_counts: Record<string, number> | null;
  interpretation: string | null;
}

export interface RunResults {
  backend: string | null;
  shots: number | null;
  task: string | null;
  code: Record<string, unknown> | null;
  noise: Record<string, unknown> | null;
  decoders: DecoderResult[];
  comparisons: Array<Record<string, unknown>>;
  decoder_limits: string | null;
  seed_streams: Record<string, number[]> | null;
  record_encoding: Record<string, string> | null;
}

export interface RunSummary {
  id: string;
  project_id: string;
  spec_id: string | null;
  status: RunStatus;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  config_hash: string | null;
  project_revision: string | null;
  error: string | null;
  exit_code: number | null;
  software_revision: string | null;
  reproduction_of: string | null;
  actor: string | null;
  scientific_status: string | null;
  artifacts_available: boolean;
  protocol?: Record<string, unknown> | null;
}

export interface RunDetail extends RunSummary {
  summary: Record<string, unknown> | null;
  results: RunResults | null;
  artifacts: Array<{ name: string; size: number; sha256: string }>;
  log_available: boolean;
  manifest: { files: Record<string, { sha256: string; size_bytes: number }> } | null;
}

export interface DecoderInfo {
  id: string;
  label: string;
  backend: string;
  description: string;
  parameters: Record<string, number>;
  available: boolean;
}

export interface CodeFamilyInfo {
  id: string;
  available: boolean;
  backend: string;
  requires: string;
}

export interface QecCapabilities {
  engine: { available: boolean; error: string | null };
  stim?: boolean;
  code_families?: string[];
  decoders?: string[];
  ui_code_families?: CodeFamilyInfo[];
  ui_decoders?: DecoderInfo[];
  capabilities?: Array<{
    name: string;
    status: string;
    evidence: string;
    limitations: string[];
  }>;
  optional_dependencies?: Record<string, boolean>;
  notice?: string;
}

export interface ExperimentTemplate {
  id: string;
  name: string;
  description: string;
  requires_stim: boolean;
  available: boolean;
  protocol: Record<string, unknown>;
}

export interface DashboardPayload {
  viewer: Viewer;
  my_projects: ProjectSummary[];
  trending_projects: ProjectSummary[];
  recent_runs: Array<
    RunSummary & { project: { full_name: string; name: string } }
  >;
  activity: ActivityEvent[];
  news: NewsFeed;
  stats: { projects: number; experiments: number };
  tools: Array<{ id: string; name: string; href: string; description: string }>;
}

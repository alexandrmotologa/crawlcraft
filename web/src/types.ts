export interface TokenStats {
  token_count: number;
  word_count: number;
  character_count: number;
  reading_time_minutes: number;
  encoding: string;
}

export interface PageMetadata {
  title?: string | null;
  description?: string | null;
  canonical_url?: string | null;
  author?: string | null;
  published_time?: string | null;
  modified_time?: string | null;
  language?: string | null;
  site_name?: string | null;
  image_url?: string | null;
  open_graph: Record<string, string>;
  json_ld: Array<Record<string, any>>;
  token_stats: TokenStats;
}

export interface CrawledPage {
  url: string;
  status_code: number;
  depth: number;
  markdown: string;
  metadata: PageMetadata;
  rendered_with: string;
  elapsed_ms: number;
  links_count: number;
  error?: string | null;
}

export interface CrawlJobStatus {
  job_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  crawled_count: number;
  failed_count: number;
  total_tokens: number;
  elapsed_seconds: number;
  pages: CrawledPage[];
}

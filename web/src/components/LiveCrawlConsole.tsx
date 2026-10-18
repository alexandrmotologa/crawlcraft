import React, { useState } from 'react';
import { CrawledPage } from '../types';
import { Search, Globe, ChevronRight, Zap, CheckCircle2, AlertCircle } from 'lucide-react';

interface Props {
  pages: CrawledPage[];
  selectedUrl: string | null;
  onSelect: (page: CrawledPage) => void;
  isRunning: boolean;
}

export const LiveCrawlConsole: React.FC<Props> = ({
  pages,
  selectedUrl,
  onSelect,
  isRunning,
}) => {
  const [filter, setFilter] = useState('');

  const filteredPages = pages.filter(p =>
    p.url.toLowerCase().includes(filter.toLowerCase()) ||
    (p.metadata.title && p.metadata.title.toLowerCase().includes(filter.toLowerCase()))
  );

  return (
    <div className="flex flex-col h-full bg-slate-900/60 rounded-xl border border-slate-800 overflow-hidden">
      {/* Search and header */}
      <div className="p-3 bg-slate-900/90 border-b border-slate-800 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Discovered Documents ({pages.length})
            </span>
            {isRunning && (
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 animate-pulse">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Live Streaming
              </span>
            )}
          </div>
        </div>

        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
          <input
            type="text"
            placeholder="Filter URLs or page titles..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
          />
        </div>
      </div>

      {/* Pages List */}
      <div className="flex-1 overflow-y-auto divide-y divide-slate-800/60">
        {filteredPages.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            {pages.length === 0 ? 'No pages crawled yet. Start a crawl above.' : 'No matching URLs found.'}
          </div>
        ) : (
          filteredPages.map((page) => {
            const isSelected = selectedUrl === page.url;
            const isSpa = page.rendered_with?.toLowerCase().includes('playwright');
            const tokenCount = page.metadata?.token_stats?.token_count ?? 0;

            return (
              <button
                key={page.url}
                onClick={() => onSelect(page)}
                className={`w-full text-left p-3 transition flex items-start justify-between gap-3 ${
                  isSelected
                    ? 'bg-emerald-500/10 border-l-2 border-emerald-500'
                    : 'hover:bg-slate-800/40'
                }`}
              >
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    {page.status_code === 200 ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                    ) : (
                      <AlertCircle className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
                    )}
                    <span className="text-xs font-semibold text-slate-200 truncate">
                      {page.metadata.title || page.url}
                    </span>
                  </div>

                  <div className="text-[11px] text-slate-400 font-mono truncate">
                    {page.url}
                  </div>

                  <div className="flex items-center gap-2 pt-1">
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                      Depth {page.depth}
                    </span>

                    {isSpa ? (
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-300 border border-purple-500/30 flex items-center gap-1">
                        <Zap className="w-2.5 h-2.5" /> SPA Headless
                      </span>
                    ) : (
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                        {page.rendered_with}
                      </span>
                    )}

                    <span className="text-[10px] text-slate-400 font-mono">
                      {tokenCount.toLocaleString()} tokens
                    </span>
                  </div>
                </div>

                <ChevronRight className={`w-4 h-4 text-slate-500 flex-shrink-0 mt-1 transition ${isSelected ? 'text-emerald-400 translate-x-0.5' : ''}`} />
              </button>
            );
          })
        )}
      </div>
    </div>
  );
};

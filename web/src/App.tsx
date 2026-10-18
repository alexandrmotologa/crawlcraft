import React, { useState } from 'react';
import {
  Globe,
  Sliders,
  Terminal,
  Activity,
  Layers,
  Sparkles,
  RefreshCw,
  FileCode2,
  FileSpreadsheet,
  Box,
  ChevronDown,
  ChevronUp,
  Cpu,
  FileText
} from 'lucide-react';
import { CrawledPage } from './types';
import { LiveCrawlConsole } from './components/LiveCrawlConsole';
import { MarkdownPreview } from './components/MarkdownPreview';
import { MetadataViewer } from './components/MetadataViewer';
import { RAGTokenStats } from './components/RAGTokenStats';
import { RagChunksViewer } from './components/RagChunksViewer';
import { PromptPackModal } from './components/PromptPackModal';

export const App: React.FC = () => {
  const [url, setUrl] = useState('https://example.com');
  const [mode, setMode] = useState<'crawl' | 'extract'>('crawl');
  const [depth, setDepth] = useState(2);
  const [maxPages, setMaxPages] = useState(25);
  const [concurrency, setConcurrency] = useState(6);
  const [rps, setRps] = useState(5.0);
  const [spaFallback, setSpaFallback] = useState(true);
  const [sameDomain, setSameDomain] = useState(true);
  const [fromSitemap, setFromSitemap] = useState(false);
  const [includeSelectors, setIncludeSelectors] = useState('');
  const [excludeSelectors, setExcludeSelectors] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [pages, setPages] = useState<CrawledPage[]>([]);
  const [selectedPage, setSelectedPage] = useState<CrawledPage | null>(null);
  const [activeTab, setActiveTab] = useState<'markdown' | 'chunks' | 'metadata'>('markdown');
  const [totalTokens, setTotalTokens] = useState(0);
  const [isPromptPackOpen, setIsPromptPackOpen] = useState(false);

  // Quick preset URLs
  const presets = [
    { label: 'Example Domain', url: 'https://example.com' },
    { label: 'FastAPI Docs', url: 'https://fastapi.tiangolo.com' },
    { label: 'Python.org', url: 'https://www.python.org' },
  ];

  const parseSelectorList = (raw: string): string[] => {
    return raw
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
  };

  // Single page extraction handler
  const handleExtract = async () => {
    setIsLoading(true);
    setPages([]);
    setSelectedPage(null);
    setTotalTokens(0);

    try {
      const res = await fetch('/v1/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url,
          allow_spa_fallback: spaFallback,
          extract_main_only: true,
          include_selectors: parseSelectorList(includeSelectors),
          exclude_selectors: parseSelectorList(excludeSelectors),
        }),
      });

      if (!res.ok) {
        throw new Error(`Extraction failed: ${res.statusText}`);
      }

      const data = await res.json();
      const pageObj: CrawledPage = {
        url: data.url,
        status_code: 200,
        depth: 0,
        markdown: data.markdown,
        metadata: data.metadata,
        rendered_with: data.rendered_with,
        elapsed_ms: data.elapsed_ms,
        links_count: 0,
      };

      setPages([pageObj]);
      setSelectedPage(pageObj);
      setTotalTokens(pageObj.metadata?.token_stats?.token_count ?? 0);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // Multi-page crawl job handler with SSE streaming
  const handleStartCrawl = async () => {
    setIsLoading(true);
    setPages([]);
    setSelectedPage(null);
    setTotalTokens(0);

    try {
      const res = await fetch('/v1/crawl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          urls: [url],
          max_depth: depth,
          max_pages: maxPages,
          concurrency,
          requests_per_second: rps,
          same_domain_only: sameDomain,
          allow_spa_fallback: spaFallback,
          extract_main_only: true,
          seed_from_sitemaps: fromSitemap,
          include_selectors: parseSelectorList(includeSelectors),
          exclude_selectors: parseSelectorList(excludeSelectors),
        }),
      });

      if (!res.ok) {
        throw new Error(`Crawl creation failed: ${res.statusText}`);
      }

      const { job_id } = await res.json();
      setActiveJobId(job_id);

      // Connect to SSE stream
      const eventSource = new EventSource(`/v1/crawl/${job_id}/stream`);

      eventSource.addEventListener('page', (evt) => {
        try {
          const payload = JSON.parse(evt.data);
          const pageData: CrawledPage = payload.data || payload;
          setPages((prev) => {
            const next = [...prev, pageData];
            if (!selectedPage && next.length === 1) {
              setSelectedPage(pageData);
            }
            return next;
          });
          setTotalTokens((prev) => prev + (pageData.metadata?.token_stats?.token_count ?? 0));
        } catch (e) {
          console.error('Failed to parse SSE page event:', e);
        }
      });

      eventSource.addEventListener('done', () => {
        eventSource.close();
        setIsLoading(false);
      });

      eventSource.onerror = () => {
        eventSource.close();
        setIsLoading(false);
      };
    } catch (err: any) {
      alert(err.message);
      setIsLoading(false);
    }
  };

  const handleExport = (format: 'jsonl' | 'markdown' | 'chunks' | 'llm_prompt') => {
    if (!activeJobId && pages.length === 0) return;
    if (activeJobId) {
      window.open(`/v1/crawl/${activeJobId}/export?format=${format}`, '_blank');
    } else {
      // Local fallback for single extract
      if (format === 'jsonl') {
        const text = pages.map((p) => JSON.stringify(p)).join('\n');
        const blob = new Blob([text], { type: 'application/x-ndjson' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = 'crawlcraft_export.jsonl';
        link.click();
      } else {
        const text = pages
          .map((p) => `# ${p.metadata.title || p.url}\n\n**Source:** ${p.url}\n\n${p.markdown}`)
          .join('\n\n---\n\n');
        const blob = new Blob([text], { type: 'text/markdown' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = 'crawlcraft_export.md';
        link.click();
      }
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Navigation */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-40 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold tracking-tight text-slate-100 text-base">CrawlCraft</span>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/30">
                v0.1.0
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Selectolax C-Parser &bull; HTTP/2 &bull; Lazy SPA Chromium</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300">
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            <span>Engine Ready</span>
          </div>

          {pages.length > 0 && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsPromptPackOpen(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs shadow transition"
              >
                <Box className="w-3.5 h-3.5" /> Pack for LLM
              </button>

              <button
                onClick={() => handleExport('jsonl')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 transition"
                title="Export JSONL dataset"
              >
                <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" /> JSONL
              </button>
              <button
                onClick={() => handleExport('markdown')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 transition"
                title="Export Combined Markdown"
              >
                <FileCode2 className="w-3.5 h-3.5 text-blue-400" /> Markdown
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Control Panel */}
      <div className="border-b border-slate-800/80 bg-slate-900/40 p-5 space-y-3">
        <div className="max-w-7xl mx-auto space-y-3">
          {/* URL Input & Mode Toggle */}
          <div className="flex flex-col md:flex-row gap-3">
            <div className="flex-1 relative">
              <Globe className="w-4 h-4 absolute left-3.5 top-3.5 text-slate-500" />
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://docs.example.com"
                className="w-full pl-10 pr-4 py-2.5 bg-slate-900/80 border border-slate-700 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition shadow-inner font-mono"
              />
            </div>

            <div className="flex items-center gap-2">
              <div className="flex p-1 bg-slate-900 rounded-xl border border-slate-800">
                <button
                  onClick={() => setMode('crawl')}
                  className={`px-3 py-2 rounded-lg text-xs font-semibold transition ${
                    mode === 'crawl' ? 'bg-emerald-500 text-slate-950 shadow-sm' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Multi-Page Crawl
                </button>
                <button
                  onClick={() => setMode('extract')}
                  className={`px-3 py-2 rounded-lg text-xs font-semibold transition ${
                    mode === 'extract' ? 'bg-emerald-500 text-slate-950 shadow-sm' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Single Extract
                </button>
              </div>

              <button
                onClick={mode === 'crawl' ? handleStartCrawl : handleExtract}
                disabled={isLoading}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-bold text-sm shadow-md transition"
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Processing...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>{mode === 'crawl' ? 'Launch Crawl' : 'Extract Document'}</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Quick Presets & Config Options */}
          <div className="flex flex-wrap items-center justify-between gap-4 pt-1 text-xs">
            <div className="flex items-center gap-2 text-slate-400">
              <span className="font-semibold text-slate-500">Presets:</span>
              {presets.map((p) => (
                <button
                  key={p.label}
                  onClick={() => setUrl(p.url)}
                  className="px-2.5 py-1 rounded-md bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-700/60 transition"
                >
                  {p.label}
                </button>
              ))}
            </div>

            <div className="flex flex-wrap items-center gap-4 text-slate-300">
              {mode === 'crawl' && (
                <>
                  <div className="flex items-center gap-1.5">
                    <span className="text-slate-400">Max Depth:</span>
                    <select
                      value={depth}
                      onChange={(e) => setDepth(Number(e.target.value))}
                      className="bg-slate-900 border border-slate-800 rounded px-2 py-0.5 text-xs text-slate-200 focus:outline-none"
                    >
                      {[1, 2, 3, 4, 5].map((d) => (
                        <option key={d} value={d}>{d}</option>
                      ))}
                    </select>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <span className="text-slate-400">Max Pages:</span>
                    <select
                      value={maxPages}
                      onChange={(e) => setMaxPages(Number(e.target.value))}
                      className="bg-slate-900 border border-slate-800 rounded px-2 py-0.5 text-xs text-slate-200 focus:outline-none"
                    >
                      {[10, 25, 50, 100, 200].map((m) => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                  </div>

                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={sameDomain}
                      onChange={(e) => setSameDomain(e.target.checked)}
                      className="rounded border-slate-800 bg-slate-900 text-emerald-500 focus:ring-0"
                    />
                    <span>Same Domain</span>
                  </label>

                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={fromSitemap}
                      onChange={(e) => setFromSitemap(e.target.checked)}
                      className="rounded border-slate-800 bg-slate-900 text-emerald-500 focus:ring-0"
                    />
                    <span>Seed from Sitemap</span>
                  </label>
                </>
              )}

              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={spaFallback}
                  onChange={(e) => setSpaFallback(e.target.checked)}
                  className="rounded border-slate-800 bg-slate-900 text-emerald-500 focus:ring-0"
                />
                <span>SPA Chromium Fallback</span>
              </label>

              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-700/60 transition"
              >
                <Sliders className="w-3.5 h-3.5 text-slate-400" />
                <span>Filters & Selectors</span>
                {showAdvanced ? <ChevronUp className="w-3 h-3 ml-0.5" /> : <ChevronDown className="w-3 h-3 ml-0.5" />}
              </button>
            </div>
          </div>

          {/* Advanced Accordion for CSS Selectors */}
          {showAdvanced && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-slate-800/80 animate-in fade-in duration-100">
              <div>
                <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                  Include CSS Selectors (comma-separated, isolates containers):
                </label>
                <input
                  type="text"
                  value={includeSelectors}
                  onChange={(e) => setIncludeSelectors(e.target.value)}
                  placeholder="e.g. article, main, #content-area"
                  className="w-full px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-emerald-500 transition font-mono"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                  Exclude CSS Selectors (comma-separated, strips noise/promos):
                </label>
                <input
                  type="text"
                  value={excludeSelectors}
                  onChange={(e) => setExcludeSelectors(e.target.value)}
                  placeholder="e.g. .newsletter-box, #social-share, .ad-banner"
                  className="w-full px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-emerald-500 transition font-mono"
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Main Workspace Split Screen */}
      <div className="flex-1 max-w-7xl w-full mx-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-0">
        {/* Left column: Discovered Pages Console */}
        <div className="lg:col-span-4 h-[720px]">
          <LiveCrawlConsole
            pages={pages}
            selectedUrl={selectedPage?.url ?? null}
            onSelect={(page) => setSelectedPage(page)}
            isRunning={isLoading}
          />
        </div>

        {/* Right column: Document Inspector & Stats */}
        <div className="lg:col-span-8 h-[720px] flex flex-col space-y-4">
          {selectedPage ? (
            <>
              {/* Token Stats Bar */}
              <RAGTokenStats
                stats={selectedPage.metadata.token_stats}
                engine={selectedPage.rendered_with}
                elapsedMs={selectedPage.elapsed_ms}
              />

              {/* Inspector Tabs */}
              <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
                <button
                  onClick={() => setActiveTab('markdown')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                    activeTab === 'markdown'
                      ? 'bg-slate-800 text-emerald-400 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" /> Synthesized Markdown
                </button>
                <button
                  onClick={() => setActiveTab('chunks')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                    activeTab === 'chunks'
                      ? 'bg-slate-800 text-emerald-400 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Layers className="w-3.5 h-3.5" /> RAG Chunks
                </button>
                <button
                  onClick={() => setActiveTab('metadata')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                    activeTab === 'metadata'
                      ? 'bg-slate-800 text-emerald-400 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Cpu className="w-3.5 h-3.5" /> Metadata & Schemas ({selectedPage.metadata.json_ld?.length || 0})
                </button>
              </div>

              {/* Tab Content */}
              <div className="flex-1 min-h-0">
                {activeTab === 'markdown' && (
                  <MarkdownPreview markdown={selectedPage.markdown} url={selectedPage.url} />
                )}
                {activeTab === 'chunks' && (
                  <RagChunksViewer
                    markdown={selectedPage.markdown}
                    url={selectedPage.url}
                    title={selectedPage.metadata.title}
                  />
                )}
                {activeTab === 'metadata' && (
                  <div className="h-full overflow-y-auto">
                    <MetadataViewer metadata={selectedPage.metadata} />
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center border border-dashed border-slate-800 rounded-xl p-12 text-center text-slate-500 space-y-3">
              <Terminal className="w-10 h-10 text-slate-600" />
              <div className="font-semibold text-slate-400 text-sm">No Document Selected</div>
              <p className="text-xs max-w-sm">
                Initiate a crawl or extraction on a web URL to inspect real-time synthesized Markdown and RAG token counts.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Prompt Pack Modal */}
      <PromptPackModal
        isOpen={isPromptPackOpen}
        onClose={() => setIsPromptPackOpen(false)}
        pages={pages}
      />
    </div>
  );
};

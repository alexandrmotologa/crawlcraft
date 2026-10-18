import React, { useState, useMemo } from 'react';
import { MarkdownChunk } from '../types';
import { Layers, Copy, Check, ChevronRight, Hash, FileJson, Search } from 'lucide-react';

interface Props {
  markdown: string;
  url: string;
  title?: string | null;
}

export const RagChunksViewer: React.FC<Props> = ({ markdown, url, title }) => {
  const [maxTokens, setMaxTokens] = useState<number>(512);
  const [search, setSearch] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Client-side markdown chunking algorithm mirroring CrawlCraft's hierarchical chunker
  const chunks: MarkdownChunk[] = useMemo(() => {
    if (!markdown.trim()) return [];

    const lines = markdown.split('\n');
    const result: MarkdownChunk[] = [];
    const breadcrumbs: string[] = [];
    let currentBlocks: string[] = [];
    let currentTokens = 0;
    let chunkIndex = 0;

    const estimateTokens = (text: string) => Math.ceil(text.length / 4.0);

    const flushChunk = () => {
      if (currentBlocks.length === 0) return;
      const content = currentBlocks.join('\n\n').trim();
      if (!content) return;

      const tCount = estimateTokens(content);
      result.push({
        chunk_id: `${url}#chunk-${chunkIndex}`,
        content,
        breadcrumbs: [...breadcrumbs],
        token_count: tCount,
        char_count: content.length,
        word_count: content.split(/\s+/).filter(Boolean).length,
        index: chunkIndex,
        metadata: { title, url },
      });
      chunkIndex++;
      currentBlocks = [];
      currentTokens = 0;
    };

    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      const headingMatch = line.match(/^(#{1,6})\s+(.*)$/);

      if (headingMatch) {
        const level = headingMatch[1].length;
        const hTitle = headingMatch[2].trim();

        while (breadcrumbs.length >= level) {
          breadcrumbs.pop();
        }
        breadcrumbs.push(hTitle);
      }

      // Check code block
      if (line.trim().startsWith('```')) {
        const codeBlockLines = [line];
        i++;
        while (i < lines.length && !lines[i].trim().startsWith('```')) {
          codeBlockLines.push(lines[i]);
          i++;
        }
        if (i < lines.length) {
          codeBlockLines.push(lines[i]);
        }
        const fullBlock = codeBlockLines.join('\n');
        const bTokens = estimateTokens(fullBlock);

        if (currentTokens + bTokens > maxTokens && currentBlocks.length > 0) {
          flushChunk();
        }
        currentBlocks.push(fullBlock);
        currentTokens += bTokens;
        i++;
        continue;
      }

      // Normal paragraph or heading line
      if (line.trim().length > 0) {
        const bTokens = estimateTokens(line);
        if (currentTokens + bTokens > maxTokens && currentBlocks.length > 0) {
          flushChunk();
        }
        currentBlocks.push(line);
        currentTokens += bTokens;
      }

      i++;
    }

    flushChunk();
    return result;
  }, [markdown, url, title, maxTokens]);

  const filteredChunks = chunks.filter((c) => {
    const q = search.toLowerCase();
    return (
      c.content.toLowerCase().includes(q) ||
      c.breadcrumbs.some((b) => b.toLowerCase().includes(q))
    );
  });

  const handleCopyChunk = (chunk: MarkdownChunk) => {
    navigator.clipboard.writeText(chunk.content);
    setCopiedId(chunk.chunk_id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleDownloadChunks = () => {
    const blob = new Blob([JSON.stringify(chunks, null, 2)], { type: 'application/json' });
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = `rag_chunks_${chunkIndexSafe(title || 'doc')}.json`;
    a.click();
    URL.revokeObjectURL(blobUrl);
  };

  const chunkIndexSafe = (str: string) => str.toLowerCase().replace(/[^a-z0-9]+/g, '_');

  return (
    <div className="flex flex-col h-full bg-slate-900/60 rounded-xl border border-slate-800 overflow-hidden">
      {/* Control bar */}
      <div className="p-3 bg-slate-900/90 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              RAG Chunks ({chunks.length})
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <span>Max Tokens:</span>
            <select
              value={maxTokens}
              onChange={(e) => setMaxTokens(Number(e.target.value))}
              className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none"
            >
              <option value={256}>256 (Dense)</option>
              <option value={512}>512 (Standard)</option>
              <option value={1024}>1024 (Broad)</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-slate-500" />
            <input
              type="text"
              placeholder="Search in chunks..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-7 pr-3 py-1 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition w-44"
            />
          </div>

          <button
            onClick={handleDownloadChunks}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 transition"
          >
            <FileJson className="w-3.5 h-3.5 text-emerald-400" /> JSON
          </button>
        </div>
      </div>

      {/* Chunks List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {filteredChunks.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            No chunks found matching query.
          </div>
        ) : (
          filteredChunks.map((chunk) => (
            <div
              key={chunk.chunk_id}
              className="p-3.5 bg-slate-950/80 border border-slate-800/80 rounded-xl space-y-2 hover:border-slate-700 transition"
            >
              <div className="flex items-center justify-between gap-2">
                {/* Breadcrumbs */}
                <div className="flex items-center gap-1 flex-wrap text-[11px] font-medium text-slate-400">
                  <span className="text-emerald-400 font-mono text-[10px]">#{chunk.index + 1}</span>
                  {chunk.breadcrumbs.length > 0 ? (
                    chunk.breadcrumbs.map((crumb, idx) => (
                      <React.Fragment key={idx}>
                        <ChevronRight className="w-3 h-3 text-slate-600" />
                        <span className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300">
                          {crumb}
                        </span>
                      </React.Fragment>
                    ))
                  ) : (
                    <span className="text-slate-500 italic">Root Content</span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    {chunk.token_count} tokens
                  </span>
                  <button
                    onClick={() => handleCopyChunk(chunk)}
                    className="p-1 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
                    title="Copy chunk text"
                  >
                    {copiedId === chunk.chunk_id ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              </div>

              {/* Chunk content */}
              <div className="p-3 bg-slate-900/40 rounded-lg border border-slate-800/60 font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
                {chunk.content}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

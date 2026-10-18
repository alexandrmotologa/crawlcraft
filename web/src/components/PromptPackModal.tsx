import React, { useState, useMemo } from 'react';
import { CrawledPage } from '../types';
import { X, Copy, Check, Download, FileCode, Box, Sparkles } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  pages: CrawledPage[];
}

export const PromptPackModal: React.FC<Props> = ({ isOpen, onClose, pages }) => {
  const [format, setFormat] = useState<'xml' | 'markdown'>('xml');
  const [systemDirective, setSystemDirective] = useState(
    'You are an expert AI assistant with access to the following curated documentation. Provide accurate, factual answers citing the relevant source URLs.'
  );
  const [copied, setCopied] = useState(false);

  const totalTokens = useMemo(() => {
    return pages.reduce((acc, p) => acc + (p.metadata?.token_stats?.token_count ?? 0), 0);
  }, [pages]);

  const packedContent = useMemo(() => {
    if (pages.length === 0) return '';

    if (format === 'xml') {
      const lines: string[] = [];
      if (systemDirective.trim()) {
        lines.push(`<system_context>\n${systemDirective.trim()}\n</system_context>\n`);
      }

      lines.push(`<knowledge_base total_documents="${pages.length}" total_tokens="${totalTokens}">`);
      lines.push('  <manifest>');
      pages.forEach((p, idx) => {
        const title = (p.metadata?.title || 'Untitled').replace(/"/g, '&quot;');
        const tokens = p.metadata?.token_stats?.token_count ?? 0;
        lines.push(`    <entry id="${idx + 1}" url="${p.url}" title="${title}" tokens="${tokens}" />`);
      });
      lines.push('  </manifest>\n');

      pages.forEach((p, idx) => {
        const title = p.metadata?.title || p.url;
        const tokens = p.metadata?.token_stats?.token_count ?? 0;
        lines.push(`  <document id="${idx + 1}" url="${p.url}" tokens="${tokens}">`);
        lines.push(`    <title>${title}</title>`);
        if (p.metadata?.description) {
          lines.push(`    <description>${p.metadata.description}</description>`);
        }
        lines.push('    <content><![CDATA[');
        lines.push(p.markdown.trim());
        lines.push('    ]]></content>');
        lines.push('  </document>\n');
      });

      lines.push('</knowledge_base>');
      return lines.join('\n');
    }

    // Markdown format
    const lines: string[] = [];
    if (systemDirective.trim()) {
      lines.push(`> **System Instructions:** ${systemDirective.trim()}\n\n---\n`);
    }

    lines.push(`# Knowledge Base (${pages.length} Documents | ${totalTokens.toLocaleString()} Tokens)\n`);
    lines.push('| ID | Document Title | Source URL | Tokens |');
    lines.push('|:---|:---|:---|:---:|');
    pages.forEach((p, idx) => {
      const title = p.metadata?.title || 'Untitled';
      const tokens = p.metadata?.token_stats?.token_count ?? 0;
      lines.push(`| ${idx + 1} | ${title} | ${p.url} | ${tokens.toLocaleString()} |`);
    });

    lines.push('\n---\n');

    pages.forEach((p, idx) => {
      lines.push(`## Document ${idx + 1}: ${p.metadata?.title || p.url}`);
      lines.push(`**URL:** ${p.url} | **Tokens:** ${(p.metadata?.token_stats?.token_count ?? 0).toLocaleString()}\n`);
      if (p.metadata?.description) {
        lines.push(`*${p.metadata.description}*\n`);
      }
      lines.push(p.markdown.trim());
      lines.push('\n\n---\n');
    });

    return lines.join('\n');
  }, [pages, format, systemDirective, totalTokens]);

  if (!isOpen) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(packedContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const ext = format === 'xml' ? 'xml' : 'md';
    const mime = format === 'xml' ? 'application/xml' : 'text/markdown';
    const blob = new Blob([packedContent], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `crawlcraft_llm_pack.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 md:p-6 animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/90">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Box className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
                Pack for LLM Prompt Context
                <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  {totalTokens.toLocaleString()} RAG Tokens
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Consolidates {pages.length} crawled pages into an injection-ready knowledge packet
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Configuration Toolbar */}
        <div className="p-4 border-b border-slate-800 bg-slate-950/40 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-400">Packet Format:</span>
              <div className="flex p-0.5 bg-slate-900 rounded-lg border border-slate-800 text-xs">
                <button
                  onClick={() => setFormat('xml')}
                  className={`px-3 py-1 rounded-md font-medium transition ${
                    format === 'xml'
                      ? 'bg-emerald-500 text-slate-950 shadow-sm font-semibold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  XML (&lt;knowledge_base&gt;)
                </button>
                <button
                  onClick={() => setFormat('markdown')}
                  className={`px-3 py-1 rounded-md font-medium transition ${
                    format === 'markdown'
                      ? 'bg-emerald-500 text-slate-950 shadow-sm font-semibold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Markdown (GFM)
                </button>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold transition shadow-sm"
              >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? 'Copied to Clipboard!' : 'Copy Context'}
              </button>

              <button
                onClick={handleDownload}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
              >
                <Download className="w-3.5 h-3.5" /> Download .{format === 'xml' ? 'xml' : 'md'}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-400 mb-1">
              System Prompt Directive (Optional):
            </label>
            <input
              type="text"
              value={systemDirective}
              onChange={(e) => setSystemDirective(e.target.value)}
              placeholder="System instructions for LLM..."
              className="w-full px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition font-sans"
            />
          </div>
        </div>

        {/* Code Preview Box */}
        <div className="flex-1 p-4 overflow-y-auto bg-slate-950 font-mono text-xs text-slate-300 leading-relaxed select-all">
          <pre className="whitespace-pre-wrap">{packedContent}</pre>
        </div>
      </div>
    </div>
  );
};

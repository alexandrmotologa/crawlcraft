import React, { useState } from 'react';
import { Copy, Check, Download, Eye, Code } from 'lucide-react';

interface Props {
  markdown: string;
  url: string;
}

export const MarkdownPreview: React.FC<Props> = ({ markdown, url }) => {
  const [tab, setTab] = useState<'preview' | 'raw'>('preview');
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = `crawlcraft_${url.replace(/[^a-zA-Z0-9]/g, '_').slice(0, 40)}.md`;
    a.click();
    URL.revokeObjectURL(blobUrl);
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/60 rounded-xl border border-slate-800 overflow-hidden">
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-900/90 border-b border-slate-800">
        <div className="flex items-center gap-1.5 p-1 bg-slate-950 rounded-lg border border-slate-800/80">
          <button
            onClick={() => setTab('preview')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              tab === 'preview'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Eye className="w-3.5 h-3.5" /> Rendered
          </button>
          <button
            onClick={() => setTab('raw')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              tab === 'raw'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Code className="w-3.5 h-3.5" /> Raw GFM
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? 'Copied!' : 'Copy'}
          </button>
          <button
            onClick={handleDownload}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
          >
            <Download className="w-3.5 h-3.5" /> Download
          </button>
        </div>
      </div>

      {/* Content pane */}
      <div className="flex-1 p-6 overflow-y-auto">
        {tab === 'raw' ? (
          <pre className="font-mono text-xs leading-relaxed text-slate-300 whitespace-pre-wrap select-text">
            {markdown || '(No markdown content extracted)'}
          </pre>
        ) : (
          <div className="prose prose-invert prose-emerald max-w-none text-slate-200 text-sm leading-relaxed space-y-4">
            {markdown ? (
              markdown.split('\n\n').map((paragraph, index) => {
                if (paragraph.startsWith('# ')) {
                  return <h1 key={index} className="text-2xl font-bold text-slate-100 pb-2 border-b border-slate-800">{paragraph.replace('# ', '')}</h1>;
                }
                if (paragraph.startsWith('## ')) {
                  return <h2 key={index} className="text-xl font-bold text-slate-100 mt-4">{paragraph.replace('## ', '')}</h2>;
                }
                if (paragraph.startsWith('### ')) {
                  return <h3 key={index} className="text-lg font-semibold text-slate-200 mt-3">{paragraph.replace('### ', '')}</h3>;
                }
                if (paragraph.startsWith('> ')) {
                  return (
                    <blockquote key={index} className="pl-4 border-l-2 border-emerald-500 text-slate-400 italic">
                      {paragraph.replace(/^>\s*/gm, '')}
                    </blockquote>
                  );
                }
                if (paragraph.startsWith('```')) {
                  const lines = paragraph.split('\n');
                  const code = lines.slice(1, -1).join('\n');
                  const lang = lines[0].replace('```', '');
                  return (
                    <div key={index} className="rounded-lg bg-slate-950 border border-slate-800 overflow-hidden my-3">
                      {lang && <div className="px-3 py-1 bg-slate-900 border-b border-slate-800 text-[11px] font-mono text-slate-400">{lang}</div>}
                      <pre className="p-4 font-mono text-xs text-emerald-400 overflow-x-auto">{code}</pre>
                    </div>
                  );
                }
                if (paragraph.startsWith('|')) {
                  // Table rendering
                  const rows = paragraph.trim().split('\n').filter(r => !r.includes('---'));
                  return (
                    <div key={index} className="overflow-x-auto my-3">
                      <table className="w-full text-left text-xs border-collapse border border-slate-800">
                        <tbody>
                          {rows.map((row, rIdx) => {
                            const cells = row.split('|').map(c => c.trim()).filter((_, i, arr) => i > 0 && i < arr.length - 1);
                            return (
                              <tr key={rIdx} className={rIdx === 0 ? "bg-slate-850 font-semibold text-slate-100 border-b border-slate-800" : "border-b border-slate-800/60"}>
                                {cells.map((cell, cIdx) => (
                                  <td key={cIdx} className="p-2 border border-slate-800/80">{cell}</td>
                                ))}
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  );
                }
                return <p key={index} className="text-slate-300 leading-relaxed">{paragraph}</p>;
              })
            ) : (
              <div className="text-slate-500 italic py-12 text-center">Empty or pending content</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

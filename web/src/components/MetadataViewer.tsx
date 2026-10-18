import React from 'react';
import { PageMetadata } from '../types';
import { Tag, Database, Globe, Calendar, User, ExternalLink } from 'lucide-react';

interface Props {
  metadata: PageMetadata;
}

export const MetadataViewer: React.FC<Props> = ({ metadata }) => {
  const hasOg = Object.keys(metadata.open_graph || {}).length > 0;
  const hasJsonLd = (metadata.json_ld || []).length > 0;

  return (
    <div className="space-y-6">
      {/* Primary Document Meta */}
      <div className="bg-slate-900/60 p-5 rounded-xl border border-slate-800 space-y-4">
        <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
          <Globe className="w-4 h-4 text-emerald-400" /> Document Head Elements
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div>
            <span className="text-slate-500 block mb-1">Title</span>
            <span className="text-slate-200 font-medium">{metadata.title || '(Not defined)'}</span>
          </div>

          <div>
            <span className="text-slate-500 block mb-1">Canonical URL</span>
            {metadata.canonical_url ? (
              <a
                href={metadata.canonical_url}
                target="_blank"
                rel="noreferrer"
                className="text-emerald-400 hover:underline flex items-center gap-1 truncate"
              >
                {metadata.canonical_url} <ExternalLink className="w-3 h-3 flex-shrink-0" />
              </a>
            ) : (
              <span className="text-slate-500">None</span>
            )}
          </div>

          <div className="md:col-span-2">
            <span className="text-slate-500 block mb-1">Meta Description</span>
            <span className="text-slate-300">{metadata.description || '(No meta description found)'}</span>
          </div>

          <div className="flex items-center gap-2">
            <User className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-slate-400">Author:</span>
            <span className="text-slate-200">{metadata.author || 'Unknown'}</span>
          </div>

          <div className="flex items-center gap-2">
            <Calendar className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-slate-400">Published:</span>
            <span className="text-slate-200">{metadata.published_time || 'N/A'}</span>
          </div>
        </div>
      </div>

      {/* OpenGraph Tags */}
      {hasOg && (
        <div className="bg-slate-900/60 p-5 rounded-xl border border-slate-800 space-y-3">
          <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
            <Tag className="w-4 h-4 text-blue-400" /> OpenGraph Metadata
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs font-mono">
            {Object.entries(metadata.open_graph).map(([key, val]) => (
              <div key={key} className="p-2 rounded bg-slate-950/80 border border-slate-800/80">
                <span className="text-blue-400 block mb-0.5">og:{key}</span>
                <span className="text-slate-300 break-all">{val}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* JSON-LD Schemas */}
      {hasJsonLd && (
        <div className="bg-slate-900/60 p-5 rounded-xl border border-slate-800 space-y-3">
          <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
            <Database className="w-4 h-4 text-purple-400" /> Schema.org JSON-LD Objects ({metadata.json_ld.length})
          </h3>
          <div className="space-y-2">
            {metadata.json_ld.map((schema, idx) => (
              <pre
                key={idx}
                className="p-3 bg-slate-950/80 rounded-lg border border-slate-800/80 text-xs font-mono text-emerald-400 overflow-x-auto max-h-60"
              >
                {JSON.stringify(schema, null, 2)}
              </pre>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

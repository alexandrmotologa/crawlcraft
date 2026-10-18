import React from 'react';
import { TokenStats } from '../types';
import { Sparkles, FileText, Clock, Cpu, Gauge } from 'lucide-react';

interface Props {
  stats: TokenStats;
  engine?: string;
  elapsedMs?: number;
}

export const RAGTokenStats: React.FC<Props> = ({ stats, engine, elapsedMs }) => {
  const density = stats.token_count > 0 ? (stats.word_count / stats.token_count).toFixed(2) : '0';

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2.5 sm:gap-3 p-3 sm:p-4 bg-slate-900/60 rounded-xl border border-slate-800">
      <div className="flex items-center gap-2.5 sm:gap-3">
        <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
          <Sparkles className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
        </div>
        <div>
          <div className="text-[10px] sm:text-xs text-slate-400 font-medium">cl100k Tokens</div>
          <div className="text-base sm:text-lg font-bold text-slate-100 font-mono">
            {stats.token_count?.toLocaleString() ?? 0}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
          <FileText className="w-4 h-4" />
        </div>
        <div>
          <div className="text-xs text-slate-400 font-medium">Word Count</div>
          <div className="text-lg font-bold text-slate-100 font-mono">
            {stats.word_count?.toLocaleString() ?? 0}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
          <Clock className="w-4 h-4" />
        </div>
        <div>
          <div className="text-xs text-slate-400 font-medium">Reading Time</div>
          <div className="text-lg font-bold text-slate-100 font-mono">
            {stats.reading_time_minutes ?? 0} <span className="text-xs text-slate-400 font-normal">min</span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
          <Gauge className="w-4 h-4" />
        </div>
        <div>
          <div className="text-xs text-slate-400 font-medium">Words/Token</div>
          <div className="text-lg font-bold text-slate-100 font-mono">{density}</div>
        </div>
      </div>

      <div className="flex items-center gap-3 col-span-2 md:col-span-1">
        <div className="w-9 h-9 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
          <Cpu className="w-4 h-4" />
        </div>
        <div>
          <div className="text-xs text-slate-400 font-medium">Engine / Latency</div>
          <div className="text-sm font-semibold text-slate-200 truncate">
            {engine || 'HTTP/2'}{elapsedMs ? ` (${elapsedMs.toFixed(0)}ms)` : ''}
          </div>
        </div>
      </div>
    </div>
  );
};

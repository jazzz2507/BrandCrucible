import React from 'react';
import type { ChallengerLog } from '../services/api';

interface Props {
  logs: ChallengerLog[];
}

export const ChallengerTrace: React.FC<Props> = ({ logs }) => {
  if (!logs || logs.length === 0) return null;

  return (
    <div className="glass-panel p-5 max-w-4xl mx-auto mb-8 font-mono text-xs relative z-10">
      <div className="flex items-center gap-2 mb-3 text-[var(--color-accent)] font-semibold uppercase tracking-wider">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--color-accent)] opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--color-accent)]"></span>
        </span>
        Challenger Audit & Cliche Filter Stream
      </div>

      <div className="space-y-3 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
        {logs.filter(log => {
          const label = log.item || log.stage.replace(/^Challenge \(/, '').replace(/\)$/, '');
          const l = label?.trim().toLowerCase();
          return l && l !== '' && l !== '?' && l !== 'undefined' && l !== 'null';
        }).map((log, idx) => {
          const label = log.item || log.stage.replace(/^Challenge \(/, '').replace(/\)$/, '');
          return (
            <div key={idx} className="bg-white/5 rounded-lg p-3 border border-white/10">
              <div className="flex justify-between items-start mb-2">
                <div className="inline-block bg-white/10 px-2 py-1 rounded text-white font-bold text-xs font-sans">
                  {label}
                </div>
              <div className={`text-[10px] font-bold px-2 py-1 rounded uppercase font-sans ${
                log.verdict === 'reject' ? 'bg-[var(--color-danger)]/20 text-[var(--color-danger)]' :
                log.verdict === 'revise' ? 'bg-amber-500/20 text-amber-500' :
                'bg-[var(--color-success)]/20 text-[var(--color-success)]'
              }`}>
                {log.verdict === 'reject' ? 'REJECTED' : log.verdict === 'revise' ? 'REVISION REQUESTED' : 'APPROVED'}
              </div>
            </div>
            <p className="text-sm text-gray-300 leading-relaxed font-sans">{log.critique}</p>
          </div>
          );
        })}
      </div>
    </div>
  );
};
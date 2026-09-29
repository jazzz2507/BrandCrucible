import React from 'react';
import type { ChallengerLog } from '../services/api';

interface Props {
  logs: ChallengerLog[];
}

export const ChallengerTrace: React.FC<Props> = ({ logs }) => {
  if (!logs || logs.length === 0) return null;

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5 rounded-xl max-w-4xl mx-auto mb-8 font-mono text-xs">
      <div className="flex items-center gap-2 mb-3 text-[var(--color-accent)] font-semibold uppercase tracking-wider">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--color-accent)] opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--color-accent)]"></span>
        </span>
        Challenger Audit & Cliche Filter Stream
      </div>

      <div className="space-y-2 max-h-48 overflow-y-auto pr-2">
        {logs.map((log, idx) => (
          <div
            key={idx}
            className={`p-2.5 rounded border ${
              log.status === 'rejected'
                ? 'border-red-500/40 bg-red-500/10 text-red-300'
                : 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
            }`}
          >
            <div className="flex justify-between font-bold mb-1">
              <span>[{log.stage}]</span>
              <span className="uppercase text-[10px] px-1.5 py-0.5 rounded bg-black/40">
                {log.status}
              </span>
            </div>
            <p className="text-gray-300 font-sans">{log.critique}</p>
          </div>
        ))}
      </div>
    </div>
  );
};
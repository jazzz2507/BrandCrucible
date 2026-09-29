import React from 'react';
import type { BrandKitData, ChallengerLog } from '../services/api';

interface Props {
  data?: BrandKitData | null;
  traceLogs?: ChallengerLog[];
}

export const BrandKitDashboard: React.FC<Props> = ({ data, traceLogs = [] }) => {
  const brandName = data?.brandName || 'Crucible AI';
  const tagline = data?.tagline || 'Forging high-velocity brand identity from raw ideas.';

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header Banner */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-6 rounded-xl">
        <span className="text-xs font-semibold text-[var(--color-accent)] uppercase tracking-wider block mb-1">
          Generated Brand Kit
        </span>
        <h1 className="text-3xl font-bold font-heading text-white">{brandName}</h1>
        <p className="text-[var(--color-muted)] mt-2 text-sm">{tagline}</p>
      </div>

      {/* Brand Identity Specs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Color Palette Card */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-6 rounded-xl space-y-4">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
            Color Palette
          </h2>
          <div className="grid grid-cols-3 gap-3">
            {(data?.palette || [
              { name: 'Primary Dark', hex: '#0B1020' },
              { name: 'Accent Teal', hex: '#00F0FF' },
              { name: 'Border Slate', hex: '#1E293B' },
            ]).map((color, idx) => (
              <div key={idx} className="space-y-2">
                <div
                  className="h-16 rounded-lg border border-white/10"
                  style={{ backgroundColor: color.hex }}
                />
                <div className="text-xs font-mono text-white font-medium">{color.name}</div>
                <div className="text-[10px] font-mono text-[var(--color-muted)]">{color.hex}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Typography & Voice Card */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-6 rounded-xl space-y-4">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
            Typography & Voice
          </h2>
          <div className="space-y-3 text-xs">
            <div>
              <div className="text-[var(--color-muted)]">Header Font</div>
              <div className="font-heading font-bold text-base text-white">
                {data?.typography?.headerFont || 'Space Grotesk'}
              </div>
            </div>
            <div>
              <div className="text-[var(--color-muted)]">Body Font</div>
              <div className="font-mono text-white">
                {data?.typography?.bodyFont || 'Inter / System Mono'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Challenger Audit Section */}
      {traceLogs.length > 0 && (
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-6 rounded-xl space-y-3">
          <h2 className="text-sm font-semibold text-[var(--color-accent)] uppercase tracking-wider">
            Challenger Audit Summary
          </h2>
          <div className="space-y-2 font-mono text-xs">
            {traceLogs.map((log, idx) => (
              <div key={idx} className="text-gray-300 border-b border-[var(--color-border)] pb-2 last:border-none">
                <span className="font-bold text-white">[{log.stage}]</span>: {log.critique}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
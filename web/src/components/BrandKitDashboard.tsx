import React from 'react';
import type { BrandKitData, ChallengerLog } from '../services/api';

interface Props {
  data?: BrandKitData | null;
  traceLogs?: ChallengerLog[];
}

export const BrandKitDashboard: React.FC<Props> = ({ data, traceLogs = [] }) => {
  const brandName = data?.brandName || 'Crucible AI';
  const tagline = data?.tagline || 'Forging high-velocity brand identity from raw ideas.';

  const valProp = data?.positioning?.value_proposition || 'Empowers users to do things better.';
  const posStatement = data?.positioning?.positioning_statement || 'For users who need X, we provide Y.';
  const traits = data?.brandShape?.personality_traits || ['Innovative', 'Bold'];
  const voice = data?.brandShape?.voice_description || 'Confident and direct.';
  
  const colDir = data?.visualIdentity?.color_direction || 'Dark mode with neon accents.';
  const typDir = data?.visualIdentity?.typography_direction || 'Modern sans-serif with a tech feel.';
  const imgDir = data?.visualIdentity?.imagery_direction || 'High contrast, abstract shapes.';

  const score = data?.consistencyCheck?.overall_score;
  const isConsistent = data?.consistencyCheck?.is_consistent;
  const consistencySummary = data?.consistencyCheck?.summary;

  return (
    <div className="max-w-4xl mx-auto space-y-8 relative z-10">
      {/* Header Banner */}
      <div className="glass-panel p-6">
        <span className="text-xs font-semibold text-[var(--color-accent)] uppercase tracking-wider block mb-1">
          Generated Brand Kit
        </span>
        <h1 className="text-3xl font-bold font-heading text-white">{brandName}</h1>
        <p className="text-[var(--color-muted)] mt-2 text-sm">{tagline}</p>

        {score !== undefined && (
          <div className="mt-4 flex items-center gap-3 border-t border-[var(--color-border)] pt-4">
             <div className={`px-2 py-1 rounded text-xs font-bold ${isConsistent ? 'bg-[var(--color-success)]/20 text-[var(--color-success)]' : 'bg-[var(--color-danger)]/20 text-[var(--color-danger)]'}`}>
                Coherence: {score}/10
             </div>
             <p className="text-xs text-[var(--color-muted)]">{consistencySummary}</p>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Positioning */}
        <div className="glass-panel p-6 space-y-4">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
            Positioning
          </h2>
          <div className="space-y-3 text-xs">
            <div>
              <div className="text-[var(--color-muted)]">Value Proposition</div>
              <div className="text-white mt-1">{valProp}</div>
            </div>
            <div>
              <div className="text-[var(--color-muted)]">Positioning Statement</div>
              <div className="text-white mt-1 italic">{posStatement}</div>
            </div>
          </div>
        </div>

        {/* Brand Shape */}
        <div className="glass-panel p-6 space-y-4">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
            Brand Shape
          </h2>
          <div className="space-y-3 text-xs">
            <div>
              <div className="text-[var(--color-muted)]">Personality Traits</div>
              <div className="flex flex-wrap gap-2 mt-1">
                {traits.map((t: string, idx: number) => (
                  <span key={idx} className="bg-white/10 px-2 py-1 rounded">{t}</span>
                ))}
              </div>
            </div>
            <div>
              <div className="text-[var(--color-muted)]">Voice Description</div>
              <div className="text-white mt-1">{voice}</div>
            </div>
          </div>
        </div>

        {/* Visual Identity */}
        <div className="glass-panel p-6 space-y-4 md:col-span-2">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
            Visual Direction
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs mb-6">
            <div>
              <div className="text-[var(--color-muted)]">Colors</div>
              <div className="text-white mt-1">{colDir}</div>
            </div>
            <div>
              <div className="text-[var(--color-muted)]">Typography</div>
              <div className="text-white mt-1">{typDir}</div>
            </div>
            <div>
              <div className="text-[var(--color-muted)]">Imagery</div>
              <div className="text-white mt-1">{imgDir}</div>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4 border-t border-[var(--color-border)]">
            <div>
              <h3 className="text-xs font-semibold text-[var(--color-muted)] uppercase tracking-wider mb-3">
                Color Palette
              </h3>
              <div className="grid grid-cols-3 gap-3">
                {(data?.palette || [
                  { name: 'Primary Dark', hex: '#0B1020' },
                  { name: 'Accent Teal', hex: '#00F0FF' },
                  { name: 'Border Slate', hex: '#1E293B' },
                ]).map((color, idx) => (
                  <div key={idx} className="space-y-2">
                    <div
                      className="h-16 rounded-lg border border-white/20 ring-1 ring-white/5"
                      style={{ backgroundColor: color.hex }}
                    />
                    <div className="text-[10px] font-mono text-white font-medium truncate">{color.name}</div>
                    <div className="text-[10px] font-mono text-[var(--color-muted)]">{color.hex}</div>
                  </div>
                ))}
              </div>
            </div>
            
            <div>
              <h3 className="text-xs font-semibold text-[var(--color-muted)] uppercase tracking-wider mb-3">
                Typography
              </h3>
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
        </div>
      </div>

      {/* Challenger Audit Section */}
      {traceLogs.length > 0 && (
        <div className="glass-panel p-6 space-y-3">
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
import React, { useState } from 'react';
import type { BrandKitData, ChallengerLog } from '../services/api';
import { derivePaletteFromDirection, deriveTypographyFromDirection } from '../services/api';

interface Props {
  data?: BrandKitData | null;
  traceLogs?: ChallengerLog[];
}

export const BrandKitDashboard: React.FC<Props> = ({ data, traceLogs = [] }) => {
  const [copied, setCopied] = useState(false);
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

  const paletteSwatches = data?.palette || derivePaletteFromDirection(colDir);
  const typographySwatches = data?.typography || deriveTypographyFromDirection(typDir);

  const handleCopy = async () => {
    if (!data) return;
    const md = `# ${brandName}
**Tagline:** ${tagline}

## Positioning
**Value Proposition:** ${valProp}
**Positioning Statement:** ${posStatement}

## Brand Shape
**Personality Traits:** ${traits.join(', ')}
**Voice Description:** ${voice}

## Visual Identity
**Color Direction:** ${colDir}
**Palette:** ${paletteSwatches.map((p: any) => `${p.name} (${p.hex})`).join(', ')}
**Typography:** ${typDir}

## Consistency Check
**Score:** ${score}/10
**Summary:** ${consistencySummary}
`;
    await navigator.clipboard.writeText(md);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!data) return;
    const blob = new Blob([JSON.stringify({ brandKit: data, traceLogs }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `brand-kit-${brandName.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 relative z-10">
      {/* Header Banner */}
      <div className="glass-panel p-6 relative">
        <div className="absolute top-6 right-6 flex gap-2">
          <button 
            onClick={handleCopy}
            className="px-3 py-1.5 text-xs font-medium bg-white/5 hover:bg-white/10 rounded transition-colors text-white"
          >
            {copied ? '✓ Copied!' : 'Copy Brand Kit'}
          </button>
          <button 
            onClick={handleDownload}
            className="px-3 py-1.5 text-xs font-medium bg-[var(--color-accent)]/20 hover:bg-[var(--color-accent)]/30 text-[var(--color-accent)] rounded transition-colors"
          >
            Download JSON
          </button>
        </div>
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
                {paletteSwatches.map((color, idx) => (
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
                    {typographySwatches.headerFont}
                  </div>
                </div>
                <div>
                  <div className="text-[var(--color-muted)]">Body Font</div>
                  <div className="font-mono text-white">
                    {typographySwatches.bodyFont}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Challenger Audit Section */}
      {traceLogs.length > 0 && (
        <div className="glass-panel p-6 space-y-4">
          <h2 className="text-sm font-semibold text-[var(--color-accent)] uppercase tracking-wider">
            Challenger Audit Summary
          </h2>
          <div className="space-y-3">
            {traceLogs.map((log, idx) => (
              <div key={idx} className="bg-white/5 rounded-lg p-4 border border-white/10">
                <div className="flex justify-between items-start mb-2">
                  <div className="inline-block bg-white/10 px-2 py-1 rounded text-white font-bold text-xs">
                    {log.item || log.stage.replace(/^Challenge \(/, '').replace(/\)$/, '')}
                  </div>
                  <div className={`text-[10px] font-bold px-2 py-1 rounded uppercase ${
                    log.verdict === 'reject' ? 'bg-[var(--color-danger)]/20 text-[var(--color-danger)]' :
                    log.verdict === 'revise' ? 'bg-amber-500/20 text-amber-500' :
                    'bg-[var(--color-success)]/20 text-[var(--color-success)]'
                  }`}>
                    {log.verdict === 'reject' ? 'REJECTED' : log.verdict === 'revise' ? 'REVISION REQUESTED' : 'APPROVED'}
                  </div>
                </div>
                <p className="text-sm text-gray-300 leading-relaxed font-sans">{log.critique}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
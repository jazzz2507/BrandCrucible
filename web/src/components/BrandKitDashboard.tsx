import React from 'react';
import { mockBrandData } from '../mocks/brandData';

export const BrandKitDashboard: React.FC = () => {
  const { brand, challengeReport } = mockBrandData;

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      {/* Hero Header */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-8 rounded-xl text-center space-y-3">
        <span className="text-xs font-semibold tracking-wider text-[var(--color-accent)] uppercase">
          Generated Brand Kit
        </span>
        <h1 className="text-4xl font-bold font-heading text-white">{brand.name}</h1>
        <p className="text-xl text-[var(--color-accent)] font-medium">"{brand.tagline}"</p>
        <p className="text-[var(--color-muted)] max-w-2xl mx-auto text-sm">{brand.positioning}</p>
      </div>

      {/* Grid Layout */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Color Palette */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-6 rounded-xl space-y-4">
          <h2 className="text-lg font-bold font-heading text-white">Color Palette</h2>
          <div className="flex gap-3">
            {brand.palette.map((color, index) => (
              <div key={index} className="flex-1 text-center space-y-1">
                <div
                  className="h-16 rounded-lg border border-[var(--color-border)] shadow-inner"
                  style={{ backgroundColor: color }}
                />
                <span className="text-xs font-mono text-[var(--color-muted)]">{color}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Challenger Audit Widget */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-6 rounded-xl space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold font-heading text-white">Challenger Audit</h2>
            <span className="px-3 py-1 text-xs font-semibold rounded-full bg-[var(--color-success)]/10 text-[var(--color-success)] border border-[var(--color-success)]/30">
              {challengeReport.verdict}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4 pt-2">
            <div className="bg-[var(--color-bg)] p-4 rounded-lg text-center border border-[var(--color-border)]">
              <span className="text-2xl font-bold text-[var(--color-danger)]">
                {challengeReport.clicheScore}%
              </span>
              <p className="text-xs text-[var(--color-muted)] mt-1">Cliché Score</p>
            </div>
            <div className="bg-[var(--color-bg)] p-4 rounded-lg text-center border border-[var(--color-border)]">
              <span className="text-2xl font-bold text-[var(--color-success)]">
                {challengeReport.distinctivenessScore}%
              </span>
              <p className="text-xs text-[var(--color-muted)] mt-1">Distinctiveness</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
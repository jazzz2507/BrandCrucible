import React, { useState } from 'react';

interface Props {
  onStartPipeline: (idea: string) => void;
  onStartGoldenDemo?: () => void;
}

export const Intake: React.FC<Props> = ({ onStartPipeline, onStartGoldenDemo }) => {
  const [idea, setIdea] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!idea.trim()) return;
    onStartPipeline(idea);
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 pt-8">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold font-heading text-white">BrandCrucible Engine</h1>
        <p className="text-[var(--color-muted)] text-sm">
          Enter a raw startup idea to trigger the 7-stage adversarial multi-agent brand engine.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="glass-panel p-6 space-y-4 relative z-10">
        <div>
          <label className="block text-xs font-semibold text-[var(--color-accent)] uppercase tracking-wider mb-2">
            Startup Idea
          </label>
          <textarea
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder="e.g., An AI app that helps college students find hackathon teammates based on skills and availability..."
            rows={4}
            className="w-full bg-[var(--color-bg)]/50 border border-[var(--color-border)] rounded-lg p-3 text-sm text-[var(--color-text)] placeholder-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] focus:border-transparent resize-none"
          />
        </div>

        <button
          type="submit"
          disabled={!idea.trim()}
          className="w-full bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] disabled:opacity-40 text-[#0B1020] font-bold py-3 rounded-lg text-sm transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--color-bg)] focus-visible:ring-[var(--color-accent)]"
        >
          Fire Up Brand Engine →
        </button>
        {onStartGoldenDemo && (
          <button
            type="button"
            onClick={onStartGoldenDemo}
            className="w-full bg-transparent border border-[var(--color-accent)] text-[var(--color-accent)] hover:bg-[var(--color-accent)]/10 font-bold py-3 rounded-lg text-sm transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--color-bg)] focus-visible:ring-[var(--color-accent)]"
          >
            ⚡ Watch Instant Golden Demo (CommonGround)
          </button>
        )}
      </form>
    </div>
  );
};
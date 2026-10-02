import React from 'react';

export const STAGES = [
  { id: 'Discover', name: '1. Discover', desc: 'Audience & problem' },
  { id: 'Position', name: '2. Position', desc: 'Value proposition' },
  { id: 'Shape', name: '3. Shape', desc: 'Naming & personality' },
  { id: 'Visualize', name: '4. Visualize', desc: 'Palette & typography' },
  { id: 'Challenge', name: '5. Challenge', desc: 'Cliché review loop' },
  { id: 'Deliver', name: '6. Deliver', desc: 'Compile brand kit' },
  { id: 'ConsistencyCheck', name: '7. Consistency Check', desc: 'Coherence audit' },
];

interface Props {
  currentStageIndex: number;
}

export const PipelineStepper: React.FC<Props> = ({ currentStageIndex }) => {
  return (
    <div className="glass-panel p-6 max-w-4xl mx-auto mb-8 relative z-10">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xs font-semibold text-[var(--color-accent)] uppercase tracking-wider">
          Multi-Agent Execution Pipeline
        </h3>
        <span className="text-xs font-mono text-[var(--color-muted)]">
          Stage {currentStageIndex + 1} of {STAGES.length}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-7 gap-2">
        {STAGES.map((stage, idx) => {
          const isComplete = idx < currentStageIndex;
          const isActive = idx === currentStageIndex;

          return (
            <div
              key={stage.id}
              className={`p-3 rounded-lg border text-xs transition-all ${
                isActive
                  ? 'border-[var(--color-accent)] bg-[var(--color-accent)]/10 text-white font-semibold shadow-[0_0_15px_rgba(255,106,61,0.2)] relative z-10 before:absolute before:inset-0 before:rounded-lg before:ring-1 before:ring-[var(--color-accent)] before:animate-pulse'
                  : isComplete
                  ? 'border-[var(--color-success)]/30 bg-[var(--color-success)]/10 text-[var(--color-success)]'
                  : 'border-[var(--color-border)] text-[var(--color-muted)] opacity-70'
              }`}
            >
              <div className="font-bold">{stage.name}</div>
              <div className="text-[10px] mt-1 text-[var(--color-muted)]">{stage.desc}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

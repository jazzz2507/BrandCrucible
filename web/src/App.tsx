import { useState, useEffect } from 'react';
import { Intake } from './components/Intake';
import { PipelineStepper, STAGES } from './components/PipelineStepper';
import { BrandKitDashboard } from './components/BrandKitDashboard';

export default function App() {
  const [viewState, setViewState] = useState<'intake' | 'running' | 'dashboard'>('intake');
  const [currentStageIndex, setCurrentStageIndex] = useState(0);

  const handleStartPipeline = (_idea: string) => {
    setViewState('running');
    setCurrentStageIndex(0);
  };

  // Simulates stepping through the 7 AI stages automatically
  useEffect(() => {
    if (viewState !== 'running') return;

    if (currentStageIndex < STAGES.length - 1) {
      const timer = setTimeout(() => {
        setCurrentStageIndex((prev) => prev + 1);
      }, 1200); // advance stage every 1.2s for demo mode
      return () => clearTimeout(timer);
    } else {
      const timer = setTimeout(() => {
        setViewState('dashboard');
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [viewState, currentStageIndex]);

  return (
    <main className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)] p-6">
      {/* Top Header Bar */}
      <header className="max-w-4xl mx-auto flex justify-between items-center pb-6 border-b border-[var(--color-border)] mb-8">
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full bg-[var(--color-accent)]" />
          <span className="font-heading font-bold text-white text-lg">BrandCrucible</span>
        </div>
        {viewState !== 'intake' && (
          <button
            onClick={() => setViewState('intake')}
            className="text-xs text-[var(--color-muted)] hover:text-white transition-colors cursor-pointer"
          >
            ← Reset Engine
          </button>
        )}
      </header>

      {/* Main Flow Views */}
      {viewState === 'intake' && <Intake onStartPipeline={handleStartPipeline} />}

      {viewState === 'running' && (
        <div className="space-y-6 pt-4">
          <PipelineStepper currentStageIndex={currentStageIndex} />
          <div className="text-center text-sm text-[var(--color-muted)] animate-pulse">
            Agent active: <span className="text-white font-semibold">{STAGES[currentStageIndex].name}</span>...
          </div>
        </div>
      )}

      {viewState === 'dashboard' && (
        <div className="space-y-6">
          <PipelineStepper currentStageIndex={STAGES.length - 1} />
          <BrandKitDashboard />
        </div>
      )}
    </main>
  );
}
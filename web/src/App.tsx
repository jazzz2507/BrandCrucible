import { useState, useEffect, useRef } from 'react';
import { Intake } from './components/Intake';
import { PipelineStepper, STAGES } from './components/PipelineStepper';
import { ChallengerTrace } from './components/ChallengerTrace';
import { BrandKitDashboard } from './components/BrandKitDashboard';
import { startPipeline, subscribeToPipelineStream } from './services/api';
import type { BrandKitData, ChallengerLog } from './services/api';

export default function App() {
  const [viewState, setViewState] = useState<'intake' | 'running' | 'dashboard'>('intake');
  const [currentStageIndex, setCurrentStageIndex] = useState(0);
  const [isSimulated, setIsSimulated] = useState(false);
  const [brandKitData, setBrandKitData] = useState<BrandKitData | null>(null);
  const [traceLogs, setTraceLogs] = useState<ChallengerLog[]>([]);
  const cleanupStreamRef = useRef<(() => void) | null>(null);

  const startSimulationMode = () => {
    setIsSimulated(true);
    setCurrentStageIndex(0);
    setTraceLogs([
      {
        stage: 'Stage 3: Position',
        critique: 'Rejected generic phrase "next-gen AI solution". Re-promoted for sharper differentiation.',
        status: 'rejected',
        timestamp: new Date().toLocaleTimeString(),
      },
      {
        stage: 'Stage 4: Shape',
        critique: 'Approved archetype "Vanguard Strategist" after filtering clichéd corporate buzzwords.',
        status: 'approved',
        timestamp: new Date().toLocaleTimeString(),
      },
    ]);
  };

  const handleStartPipeline = async (idea: string) => {
    setViewState('running');
    setCurrentStageIndex(0);
    setTraceLogs([]);
    setIsSimulated(false);

    try {
      const sessionId = await startPipeline(idea);

      cleanupStreamRef.current = subscribeToPipelineStream(
        sessionId,
        (event) => {
          if (typeof event.stageIndex === 'number') {
            setCurrentStageIndex(event.stageIndex);
          }
          if (event.traceLog) {
            setTraceLogs((prev) => [...prev, event.traceLog!]);
          }
          if (event.traceLogs?.length) {
            setTraceLogs((prev) => [...prev, ...event.traceLogs!]);
          }
          if (event.payload) {
            setBrandKitData((prev) => ({ ...prev, ...event.payload }));
          }
          if (event.isComplete === true) {
            setTimeout(() => setViewState('dashboard'), 1200);
          }
        },
        (_err) => {
          console.warn('Backend connection failed. Switching to demo simulation mode.');
          startSimulationMode();
        }
      );
    } catch (_error) {
      console.warn('Backend endpoint unreachable. Falling back to demo simulation mode.');
      startSimulationMode();
    }
  };

  const handleStartGoldenDemo = () => {
    setViewState('running');
    setCurrentStageIndex(0);
    setTraceLogs([]);
    setIsSimulated(false);

    cleanupStreamRef.current = subscribeToPipelineStream(
      'golden-demo',
      (event) => {
        if (typeof event.stageIndex === 'number') {
          setCurrentStageIndex(event.stageIndex);
        }
        if (event.traceLog) {
          setTraceLogs((prev) => [...prev, event.traceLog!]);
        }
        if (event.traceLogs?.length) {
          setTraceLogs((prev) => [...prev, ...event.traceLogs!]);
        }
        if (event.payload) {
          setBrandKitData((prev) => ({ ...prev, ...event.payload }));
        }
        if (event.isComplete === true) {
          setTimeout(() => setViewState('dashboard'), 1200);
        }
      },
      (_err) => {
        console.warn('Backend connection failed. Switching to demo simulation mode.');
        startSimulationMode();
      }
    );
  };

  useEffect(() => {
    if (viewState !== 'running' || !isSimulated) return;

    if (currentStageIndex < STAGES.length - 1) {
      const timer = setTimeout(() => {
        setCurrentStageIndex((prev) => prev + 1);
      }, 1200);
      return () => clearTimeout(timer);
    } else {
      const timer = setTimeout(() => {
        setViewState('dashboard');
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [viewState, currentStageIndex, isSimulated]);

  useEffect(() => {
    return () => {
      if (cleanupStreamRef.current) cleanupStreamRef.current();
    };
  }, []);

  return (
    <main className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)] p-6">
      <header className="max-w-4xl mx-auto flex justify-between items-center pb-6 border-b border-[var(--color-border)] mb-8">
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full bg-[var(--color-accent)]" />
          <span className="font-heading font-bold text-white text-lg">BrandCrucible</span>
          {isSimulated && viewState === 'running' && (
            <span className="text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded ml-2">
              Demo Simulation
            </span>
          )}
        </div>
        {viewState !== 'intake' && (
          <button
            onClick={() => setViewState('intake')}
            className="text-xs text-[var(--color-muted)] hover:text-white transition-colors cursor-pointer"
          >
            ← Back to Input
          </button>
        )}
      </header>

      {viewState === 'intake' && <Intake onStartPipeline={handleStartPipeline} onStartGoldenDemo={handleStartGoldenDemo} />}

      {viewState === 'running' && (
        <div className="space-y-6">
          <PipelineStepper currentStageIndex={currentStageIndex} />
          <ChallengerTrace logs={traceLogs} />
          <div className="text-center font-mono text-xs text-[var(--color-muted)] animate-pulse">
            Processing stage through multi-agent engine...
          </div>
        </div>
      )}

      {viewState === 'dashboard' && <BrandKitDashboard data={brandKitData} traceLogs={traceLogs} />}
    </main>
  );
}
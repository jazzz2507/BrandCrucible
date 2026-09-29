const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export type ChallengerLog = {
  stage: string;
  critique: string;
  status: 'approved' | 'rejected';
  timestamp: string;
};

export type BrandKitData = {
  brandName?: string;
  tagline?: string;
  description?: string;
  palette?: Array<{ name: string; hex: string }>;
  typography?: { headerFont: string; bodyFont: string };
  challengerLogs?: ChallengerLog[];
  [key: string]: any;
};

export type PipelineStreamEvent = {
  stageIndex: number;
  stageName?: string;
  payload?: BrandKitData;
  traceLog?: ChallengerLog;
  isComplete?: boolean;
};

const STAGE_IDS = ['Interviewer', 'Discover', 'Position', 'Shape', 'Visualize', 'Challenge', 'Deliver'];

function stageIndexFor(stageId: string | undefined): number {
  if (!stageId) return 0;
  const idx = STAGE_IDS.indexOf(stageId);
  return idx === -1 ? 0 : idx;
}

export async function startPipeline(idea: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/api/interview/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ idea }),
  });

  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }

  const data = await response.json();
  return data.sessionId || data.id || 'demo-session';
}

export function subscribeToPipelineStream(
  sessionId: string,
  onEvent: (event: PipelineStreamEvent) => void,
  onError: (error: any) => void
): () => void {
  const eventSource = new EventSource(`${API_BASE_URL}/api/pipeline/stream/${sessionId}`);

  // A stage has started
  eventSource.addEventListener('stage_start', (e: MessageEvent) => {
    try {
      const data = JSON.parse(e.data);
      onEvent({
        stageIndex: stageIndexFor(data.stage),
        stageName: data.stage,
      });
    } catch (err) {
      console.error('Failed to parse stage_start payload:', err);
    }
  });

  // A stage finished — may carry a challenger critique or partial brand data
  eventSource.addEventListener('stage_complete', (e: MessageEvent) => {
    try {
      const data = JSON.parse(e.data);
      onEvent({
        stageIndex: stageIndexFor(data.stage),
        stageName: data.stage,
        payload: data.payload,
        traceLog: data.traceLog,
      });
    } catch (err) {
      console.error('Failed to parse stage_complete payload:', err);
    }
  });

  // Pipeline fully finished — CRITICAL: close the connection or the browser
  // will auto-reconnect and restart the whole pipeline in a loop.
  eventSource.addEventListener('done', (e: MessageEvent) => {
    try {
      const data = e.data ? JSON.parse(e.data) : {};
      onEvent({
        stageIndex: STAGE_IDS.length - 1,
        payload: data.payload,
        isComplete: true,
      });
    } catch (err) {
      console.error('Failed to parse done payload:', err);
    } finally {
      eventSource.close();
    }
  });

  // Server explicitly sent an error event
  eventSource.addEventListener('error', (e: any) => {
    // Only treat as a real error if the connection is actually closed/broken.
    // A named "error" event with data is a backend-reported error, not a network drop.
    if (e.data) {
      try {
        const data = JSON.parse(e.data);
        onError(data);
      } catch {
        onError(e);
      }
    } else if (eventSource.readyState === EventSource.CLOSED) {
      onError(e);
    }
    eventSource.close();
  });

  return () => {
    eventSource.close();
  };
}
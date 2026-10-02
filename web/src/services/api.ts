const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export type ChallengerLog = {
  stage: string;
  critique: string;
  status: 'approved' | 'rejected';
  timestamp: string;
  item?: string;
  itemType?: string;
  verdict?: 'pass' | 'revise' | 'reject';
};

export type BrandKitData = {
  brandName?: string;
  tagline?: string;
  description?: string;
  discovery?: any;
  positioning?: any;
  brandShape?: any;
  visualIdentity?: any;
  consistencyCheck?: any;
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
  traceLogs?: ChallengerLog[];
  isComplete?: boolean;
};

const STAGE_IDS = ['Discover', 'Position', 'Shape', 'Visualize', 'Challenge', 'Deliver', 'ConsistencyCheck'];

function stageIndexFor(stageId: string | undefined): number {
  if (!stageId) return 0;
  const idx = STAGE_IDS.indexOf(stageId);
  return idx === -1 ? 0 : idx;
}

export function derivePaletteFromDirection(colorDirection?: string): Array<{ name: string; hex: string }> {
  const text = (colorDirection || '').toLowerCase();
  
  const rules = [
    { match: ['galvanized steel', 'steel gray'], color: { name: 'Galvanized Steel', hex: '#4A5568' } },
    { match: ['timber brown', 'workbench', 'wood'], color: { name: 'Workbench Timber', hex: '#7C4A27' } },
    { match: ['hazard yellow', 'safety yellow', 'yellow'], color: { name: 'Hazard Yellow', hex: '#FACC15' } },
    { match: ['terracotta', 'ember', 'rust'], color: { name: 'Forge Ember', hex: '#F97316' } },
    { match: ['forest', 'sage', 'emerald', 'green'], color: { name: 'Forest Sage', hex: '#15803D' } },
    { match: ['navy', 'cobalt', 'indigo'], color: { name: 'Deep Navy', hex: '#1E3A8A' } },
    { match: ['cream', 'ivory', 'alabaster', 'sand'], color: { name: 'Warm Ivory', hex: '#F5F5F4' } },
    { match: ['charcoal', 'obsidian', 'matte black'], color: { name: 'Matte Obsidian', hex: '#18181B' } },
    { match: ['slate'], color: { name: 'Slate Grey', hex: '#334155' } },
    { match: ['crimson', 'burgundy', 'coral'], color: { name: 'Crimson Clay', hex: '#DC2626' } },
    { match: ['teal', 'cyan'], color: { name: 'Industrial Teal', hex: '#0D9488' } }
  ];

  const matchedColors: Array<{ name: string; hex: string }> = [];
  
  for (const rule of rules) {
    if (rule.match.some(m => text.includes(m))) {
      matchedColors.push(rule.color);
    }
  }

  const hexMatches = text.match(/#[0-9A-Fa-f]{6}/g) || [];
  for (const hex of hexMatches) {
    if (!matchedColors.some(c => c.hex.toUpperCase() === hex.toUpperCase())) {
      matchedColors.push({ name: `Hex ${hex.toUpperCase()}`, hex: hex.toUpperCase() });
    }
  }

  // Deduplicate by hex
  const uniqueColors = matchedColors.filter((c, index, self) =>
    index === self.findIndex((t) => t.hex.toUpperCase() === c.hex.toUpperCase())
  );

  const defaults = [
    { name: 'Obsidian Base', hex: '#121318' },
    { name: 'Forge Ember', hex: '#FF6B2B' },
    { name: 'Warm Stone', hex: '#2A2D37' }
  ];

  while (uniqueColors.length < 3) {
    uniqueColors.push(defaults[uniqueColors.length]);
  }

  return uniqueColors.slice(0, 3);
}

export function deriveTypographyFromDirection(typographyDirection?: string): { headerFont: string; bodyFont: string } {
  const text = (typographyDirection || '').toLowerCase();
  
  if (text.includes('serif') && !text.includes('sans-serif')) {
    return { headerFont: 'Merriweather', bodyFont: 'Georgia' };
  } else if (text.includes('mono')) {
    return { headerFont: 'Fira Code', bodyFont: 'Roboto Mono' };
  } else if (text.includes('roboto') || text.includes('helvetica')) {
    return { headerFont: 'Roboto', bodyFont: 'Open Sans' };
  }
  
  return { headerFont: 'Space Grotesk', bodyFont: 'Inter' };
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
      let traceLogs: ChallengerLog[] | undefined;
      let payload: BrandKitData | undefined;

      if (data.stage === 'Challenge' && Array.isArray(data.output?.items)) {
        traceLogs = data.output.items.map((item: any) => {
          const h = item.history && item.history.length ? item.history[item.history.length - 1] : { feedback: item.feedback, verdict: item.verdict };
          return {
            stage: `Challenge (${item.type}: ${item.value || item.item || '?'})`,
            critique: h.feedback || item.feedback,
            status: (h.verdict || item.verdict) === 'pass' ? 'approved' : 'rejected',
            timestamp: new Date().toISOString(),
            item: item.value || item.item,
            itemType: item.type,
            verdict: (h.verdict || item.verdict)?.toLowerCase()
          } as ChallengerLog;
        });
      }
      
      if (data.stage === 'Deliver' && data.output) {
        const out = data.output;
        payload = {
          brandName: out.brand_name,
          tagline: out.tagline,
          discovery: out.discovery,
          positioning: out.positioning,
          brandShape: out.brand_shape,
          visualIdentity: out.visual_identity,
        };
      }

      onEvent({
        stageIndex: stageIndexFor(data.stage),
        stageName: data.stage,
        payload: payload || data.payload,
        traceLog: data.traceLog,
        traceLogs: traceLogs,
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
      let payload: BrandKitData | undefined;
      let traceLogs: ChallengerLog[] = [];
      
      if (Array.isArray(data.trace)) {
        const itemMap = new Map<string, ChallengerLog>();
        data.trace.forEach((entry: any) => {
          if (entry.stage === 'Challenge' && entry.rawResponse) {
            try {
              const parsed = JSON.parse(entry.rawResponse);
              if (parsed.item && parsed.verdict) {
                const log = {
                  stage: `Challenge (${parsed.item})`,
                  critique: parsed.feedback,
                  status: parsed.verdict === 'pass' ? 'approved' : 'rejected',
                  timestamp: entry.timestamp || new Date().toISOString(),
                  item: parsed.item,
                  itemType: parsed.type,
                  verdict: parsed.verdict.toLowerCase()
                } as ChallengerLog;
                itemMap.set(parsed.item, log);
              }
            } catch (err) {}
          }
        });
        traceLogs = Array.from(itemMap.values());
      }
      
      if (data.brandKit || data.consistencyCheck) {
        const out = data.brandKit || {};
        payload = {
          brandName: out.brand_name,
          tagline: out.tagline,
          discovery: out.discovery,
          positioning: out.positioning,
          brandShape: out.brand_shape,
          visualIdentity: out.visual_identity,
          consistencyCheck: data.consistencyCheck,
        };
      }

      onEvent({
        stageIndex: STAGE_IDS.length - 1,
        payload: payload || data.payload,
        traceLogs: traceLogs.length > 0 ? traceLogs : undefined,
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
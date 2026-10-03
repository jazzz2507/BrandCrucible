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
  const text = (colorDirection || '').trim();
  if (!text) {
    return [
      { name: 'Obsidian Base', hex: '#121318' },
      { name: 'Forge Ember', hex: '#FF6B2B' },
      { name: 'Warm Stone', hex: '#2A2D37' }
    ];
  }

  const matchedColors: Array<{ name: string; hex: string }> = [];
  const seenHex = new Set<string>();

  // 1. Explicitly bound name + hex pairs in text: e.g. "Electric Lime (#39FF14)" or "Primary: Electric Lime (#39FF14)"
  const nameHexRegex = /([A-Za-z0-9\s\-]+?)\s*[:\(]\s*(#[0-9A-Fa-f]{6})\)?/gi;
  let m: RegExpExecArray | null;
  while ((m = nameHexRegex.exec(text)) !== null) {
    const rawName = m[1].trim();
    const hex = m[2].toUpperCase();
    const parts = rawName.split(/[,;:\.\n]|(?:\b(?:featuring|with|and|by|of|the|is|in|palette|primary|secondary|accent|base|neutral|hero)\b)/i);
    let candidate = (parts.length > 0 ? parts[parts.length - 1] : rawName).trim();
    candidate = candidate.replace(/^(?:a|an|the|as|for|deep|bright|dark|light)\s+/i, '').trim();
    const words = candidate.split(/\s+/).filter(Boolean);
    const trimmedWords = words.length > 3 ? words.slice(-3) : words;
    const formattedName = trimmedWords
      .map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
      .join(' ');
    if (formattedName.length > 1 && !seenHex.has(hex)) {
      matchedColors.push({ name: formattedName, hex });
      seenHex.add(hex);
      if (matchedColors.length >= 3) return matchedColors;
    }
  }

  // 2. Curated rule keywords matched by their order of appearance in prose
  const rules = [
    { match: ['electric lime', 'lime', 'neon green'], color: { name: 'Electric Lime', hex: '#39FF14' } },
    { match: ['electric cyan', 'cyan', 'neon blue'], color: { name: 'Electric Cyan', hex: '#00F0FF' } },
    { match: ['hot coral', 'coral', 'crimson', 'burgundy'], color: { name: 'Hot Coral', hex: '#FF6F61' } },
    { match: ['galvanized steel', 'steel gray', 'steel grey', 'steel'], color: { name: 'Galvanized Steel', hex: '#4A5568' } },
    { match: ['timber brown', 'workbench timber', 'workbench', 'wood'], color: { name: 'Workbench Timber', hex: '#7C4A27' } },
    { match: ['hazard yellow', 'safety yellow', 'solar yellow', 'yellow'], color: { name: 'Hazard Yellow', hex: '#FACC15' } },
    { match: ['terracotta', 'forge ember', 'ember', 'rust'], color: { name: 'Forge Ember', hex: '#F97316' } },
    { match: ['forest sage', 'forest', 'sage', 'emerald', 'green'], color: { name: 'Forest Sage', hex: '#15803D' } },
    { match: ['deep navy', 'navy', 'cobalt', 'indigo'], color: { name: 'Deep Navy', hex: '#1E3A8A' } },
    { match: ['warm ivory', 'ivory', 'alabaster', 'cream', 'sand'], color: { name: 'Warm Ivory', hex: '#F5F5F4' } },
    { match: ['matte obsidian', 'charcoal', 'obsidian', 'matte black', 'black'], color: { name: 'Matte Obsidian', hex: '#18181B' } },
    { match: ['slate grey', 'slate gray', 'slate'], color: { name: 'Slate Grey', hex: '#334155' } },
    { match: ['industrial teal', 'teal'], color: { name: 'Industrial Teal', hex: '#0D9488' } }
  ];

  const lowerText = text.toLowerCase();
  const ruleHits: Array<{ pos: number; color: { name: string; hex: string } }> = [];
  for (const rule of rules) {
    let earliest = -1;
    for (const kw of rule.match) {
      const idx = lowerText.indexOf(kw);
      if (idx !== -1 && (earliest === -1 || idx < earliest)) {
        earliest = idx;
      }
    }
    if (earliest !== -1) {
      ruleHits.push({ pos: earliest, color: rule.color });
    }
  }

  ruleHits.sort((a, b) => a.pos - b.pos);
  for (const hit of ruleHits) {
    const hex = hit.color.hex.toUpperCase();
    if (!seenHex.has(hex)) {
      matchedColors.push({ name: hit.color.name, hex });
      seenHex.add(hex);
      if (matchedColors.length >= 3) return matchedColors;
    }
  }

  // 3. Standalone hex codes
  const hexMatches = text.match(/#[0-9A-Fa-f]{6}/g) || [];
  for (const rawHex of hexMatches) {
    const hex = rawHex.toUpperCase();
    if (!seenHex.has(hex)) {
      matchedColors.push({ name: `Hex ${hex}`, hex });
      seenHex.add(hex);
      if (matchedColors.length >= 3) return matchedColors;
    }
  }

  // 4. Default fallbacks
  const defaults = [
    { name: 'Obsidian Base', hex: '#121318' },
    { name: 'Forge Ember', hex: '#FF6B2B' },
    { name: 'Warm Stone', hex: '#2A2D37' }
  ];

  for (const d of defaults) {
    if (matchedColors.length < 3 && !seenHex.has(d.hex.toUpperCase())) {
      matchedColors.push(d);
      seenHex.add(d.hex.toUpperCase());
    }
  }

  return matchedColors.slice(0, 3);
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
        traceLogs = data.output.items.flatMap((item: any) => {
          return (item.history || []).map((h: any) => {
            const cardLabel = h.item || h.candidate || h.target || h.name || h.value || '';
            const critiqueText = h.feedback || h.explanation || h.critique || '';
            const verdictVal = h.verdict || 'pass';

            return {
              stage: `Challenge (${item.type || 'audit'}: ${cardLabel})`,
              critique: critiqueText,
              status: verdictVal === 'pass' ? 'approved' : 'rejected',
              timestamp: new Date().toISOString(),
              item: cardLabel,
              itemType: item.type,
              verdict: verdictVal?.toLowerCase()
            } as ChallengerLog;
          });
        }).filter((log: ChallengerLog) => {
          const l = log.item?.trim().toLowerCase();
          const hasCritique = log.critique?.trim().length > 0;
          return l && l !== '' && l !== '?' && l !== 'undefined' && l !== 'null' && hasCritique;
        });
      }
      
      if (data.stage === 'Visualize' && data.output) {
        const out = data.output;
        const rawPalette = out.palette;
        let palette: Array<{ name: string; hex: string }> | undefined;
        if (Array.isArray(rawPalette) && rawPalette.length > 0) {
          palette = rawPalette.map((p: any) => typeof p === 'string' ? { name: p, hex: p } : p);
        } else {
          palette = derivePaletteFromDirection(out.color_direction);
        }
        payload = {
          visualIdentity: out,
          palette,
        };
      }
      
      if (data.stage === 'Deliver' && data.output) {
        const out = data.output;
        const rawPalette = out.palette || out.visual_identity?.palette;
        let palette: Array<{ name: string; hex: string }> | undefined;
        if (Array.isArray(rawPalette) && rawPalette.length > 0) {
          palette = rawPalette.map((p: any) => typeof p === 'string' ? { name: p, hex: p } : p);
        } else {
          palette = derivePaletteFromDirection(out.visual_identity?.color_direction);
        }
        payload = {
          brandName: out.brand_name,
          tagline: out.tagline,
          discovery: out.discovery,
          positioning: out.positioning,
          brandShape: out.brand_shape,
          visualIdentity: out.visual_identity,
          palette,
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
      eventSource.close();
      const data = e.data ? JSON.parse(e.data) : {};
      let payload: BrandKitData | undefined;
      let traceLogs: ChallengerLog[] = [];
      
      if (data.challengeOutput && Array.isArray(data.challengeOutput.items)) {
        traceLogs = data.challengeOutput.items.flatMap((item: any) => {
          return (item.history || []).map((h: any) => {
            const cardLabel = h.item || h.candidate || h.target || h.name || h.value || '';
            const critiqueText = h.feedback || h.explanation || h.critique || '';
            const verdictVal = h.verdict || 'pass';

            return {
              stage: `Challenge (${item.type || 'audit'}: ${cardLabel})`,
              critique: critiqueText,
              status: verdictVal === 'pass' ? 'approved' : 'rejected',
              timestamp: h.timestamp || new Date().toISOString(),
              item: cardLabel,
              itemType: item.type,
              verdict: verdictVal?.toLowerCase()
            } as ChallengerLog;
          });
        }).filter((log: ChallengerLog) => {
          const l = log.item?.trim().toLowerCase();
          const hasCritique = log.critique?.trim().length > 0;
          return l && l !== '' && l !== '?' && l !== 'undefined' && l !== 'null' && hasCritique;
        });
      } else if (Array.isArray(data.trace)) {
        const itemMap = new Map<string, ChallengerLog>();
        data.trace.forEach((entry: any) => {
          if (entry.stage === 'Challenge' && entry.rawResponse) {
            try {
              const parsed = JSON.parse(entry.rawResponse);
              const itemName = parsed.item || parsed.target || parsed.candidate || parsed.name || parsed.value || '';
              const critiqueText = parsed.feedback || parsed.explanation || parsed.critique || '';
              if (itemName && parsed.verdict) {
                let cardLabel = itemName.trim();
                const l = cardLabel.toLowerCase();
                const hasCritique = critiqueText?.trim().length > 0;
                if (l && l !== '' && l !== '?' && l !== 'undefined' && l !== 'null' && hasCritique) {
                  const log = {
                    stage: `Challenge (${cardLabel})`,
                    critique: critiqueText,
                    status: parsed.verdict === 'pass' ? 'approved' : 'rejected',
                    timestamp: entry.timestamp || new Date().toISOString(),
                    item: cardLabel,
                    itemType: parsed.type,
                    verdict: parsed.verdict.toLowerCase()
                  } as ChallengerLog;
                  itemMap.set(cardLabel, log);
                }
              }
            } catch (err) {}
          }
        });
        traceLogs = Array.from(itemMap.values());
      }
      
      if (data.brandKit || data.consistencyCheck) {
        const out = data.brandKit || {};
        const rawPalette = out.palette || out.visual_identity?.palette;
        let palette: Array<{ name: string; hex: string }> | undefined;
        if (Array.isArray(rawPalette) && rawPalette.length > 0) {
          palette = rawPalette.map((p: any) => typeof p === 'string' ? { name: p, hex: p } : p);
        } else {
          palette = derivePaletteFromDirection(out.visual_identity?.color_direction);
        }
        payload = {
          brandName: out.brand_name,
          tagline: out.tagline,
          discovery: out.discovery,
          positioning: out.positioning,
          brandShape: out.brand_shape,
          visualIdentity: out.visual_identity,
          palette,
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
    }
  });

  // Server explicitly sent an error event
  eventSource.addEventListener('error', (e: any) => {
    eventSource.close();
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
  });

  return () => {
    eventSource.close();
  };
}
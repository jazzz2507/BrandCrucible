const events = [];

export function logTraceEvent(stageName, input, output, meta = {}) {
  const event = {
    id: `${Date.now()}-${events.length + 1}`,
    timestamp: new Date().toISOString(),
    stage: stageName,
    input,
    output,
    score: meta.score ?? output?.scores ?? null,
    meta,
  };
  events.push(event);
  return event;
}

export function getTraceLog() {
  return events.map((event) => ({ ...event }));
}

export function dumpTraceLog() {
  return JSON.stringify(getTraceLog(), null, 2);
}

export function clearTraceLog() {
  events.length = 0;
}

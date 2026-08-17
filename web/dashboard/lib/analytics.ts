export type AnalyticsProperties = Record<string, string | number | boolean | null | undefined>

export function trackEvent(name: string, properties: AnalyticsProperties = {}) {
  if (typeof window === 'undefined') return
  const event = {
    name,
    properties,
    path: window.location.pathname,
    timestamp: new Date().toISOString(),
  }
  const w = window as Window & { __SOLVABLE_EVENTS__?: typeof event[] }
  w.__SOLVABLE_EVENTS__ = [...(w.__SOLVABLE_EVENTS__ || []).slice(-99), event]
  window.dispatchEvent(new CustomEvent('solvable:analytics', { detail: event }))
  try {
    const stored = JSON.parse(window.localStorage.getItem('solvable.analytics') || '[]') as typeof event[]
    window.localStorage.setItem('solvable.analytics', JSON.stringify([...stored.slice(-99), event]))
  } catch { /* analytics must never block a product action */ }
}

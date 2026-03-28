// frontend/src/utils/constants.js
//
// All magic strings and config values in one place.
// Never hardcode these inline in components.

// ── Intent labels (must match backend classifier output exactly) ──
export const INTENT_LABELS = {
  ANSWER:       'answer',
  SUMMARISE:    'summarise',
  OUT_OF_SCOPE: 'out-of-scope',
}

// ── Intent badge colours (Tailwind classes) ────────────────────────
// Each intent gets a background + text colour pair.
export const INTENT_COLORS = {
  [INTENT_LABELS.ANSWER]: {
    bg:   'bg-emerald-500/20',
    text: 'text-emerald-400',
    border: 'border-emerald-500/30',
    dot:  'bg-emerald-400',
    label: 'Answer',
  },
  [INTENT_LABELS.SUMMARISE]: {
    bg:   'bg-blue-500/20',
    text: 'text-blue-400',
    border: 'border-blue-500/30',
    dot:  'bg-blue-400',
    label: 'Summarise',
  },
  [INTENT_LABELS.OUT_OF_SCOPE]: {
    bg:   'bg-slate-500/20',
    text: 'text-slate-400',
    border: 'border-slate-500/30',
    dot:  'bg-slate-400',
    label: 'Out of Scope',
  },
}

// ── File upload constraints (must match backend config) ────────────
export const MAX_FILE_SIZE_MB  = 20
export const ACCEPTED_MIME     = 'application/pdf'
export const ACCEPTED_EXT      = '.pdf'

// ── Session storage key ────────────────────────────────────────────
// We store session_id in sessionStorage (clears on tab close).
// This means closing the tab = new session on next open.
// Intentional: keeps local-app behaviour simple.
export const SESSION_STORAGE_KEY = 'study_assistant_session_id'

// ── Retrieval scope ────────────────────────────────────────────────
export const SCOPE_ALL = 'all'

// ── API base ───────────────────────────────────────────────────────
// Vite proxy forwards /api → localhost:8000
// So we never hardcode the backend port in frontend code.
export const API_BASE = '/api/v1'
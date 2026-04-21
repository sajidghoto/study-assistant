// frontend/src/utils/constants.js

export const INTENT_LABELS = {
  ANSWER:    'answer',
  EXPLAIN:   'explain',
  SUMMARISE: 'summarise',
  COMPARE:   'compare',
  QUIZ:      'quiz',
}

export const INTENT_COLORS = {
  answer: {
    bg:     'bg-emerald-500/20',
    text:   'text-emerald-400',
    border: 'border-emerald-500/30',
    dot:    'bg-emerald-400',
    label:  'Answer',
  },
  explain: {
    bg:     'bg-violet-500/20',
    text:   'text-violet-400',
    border: 'border-violet-500/30',
    dot:    'bg-violet-400',
    label:  'Explain',
  },
  summarise: {
    bg:     'bg-blue-500/20',
    text:   'text-blue-400',
    border: 'border-blue-500/30',
    dot:    'bg-blue-400',
    label:  'Summarise',
  },
  compare: {
    bg:     'bg-amber-500/20',
    text:   'text-amber-400',
    border: 'border-amber-500/30',
    dot:    'bg-amber-400',
    label:  'Compare',
  },
  quiz: {
    bg:     'bg-rose-500/20',
    text:   'text-rose-400',
    border: 'border-rose-500/30',
    dot:    'bg-rose-400',
    label:  'Quiz',
  },
}

export const MAX_FILE_SIZE_MB    = 20
export const ACCEPTED_MIME       = 'application/pdf'
export const ACCEPTED_EXT        = '.pdf'
export const SESSION_STORAGE_KEY = 'study_assistant_session_id'
export const QUIZ_HISTORY_KEY    = 'study_assistant_quiz_history'
export const SCOPE_ALL           = 'all'
export const API_BASE            = '/api/v1'
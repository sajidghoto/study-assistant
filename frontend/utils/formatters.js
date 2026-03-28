// frontend/src/utils/formatters.js
//
// Pure utility functions. No side effects, no imports.
// Each function takes a value and returns a formatted string.

/**
 * Format a cosine similarity score as a percentage string.
 * e.g. 0.8734 → "87%"
 */
export function formatScore(score) {
  return `${Math.round(score * 100)}%`
}

/**
 * Truncate text to a maximum character count, adding ellipsis.
 * Used in SourcesPanel to show a preview of each chunk.
 * e.g. truncateText("hello world", 5) → "hello..."
 */
export function truncateText(text, maxChars = 150) {
  if (!text || text.length <= maxChars) return text
  return text.slice(0, maxChars).trimEnd() + '...'
}

/**
 * Format a confidence score as a rounded percentage.
 * e.g. 0.9412 → "94%"
 */
export function formatConfidence(confidence) {
  return `${Math.round(confidence * 100)}%`
}

/**
 * Format an ISO datetime string to a human-readable local time.
 * e.g. "2026-03-27T10:30:00Z" → "10:30 AM"
 */
export function formatTime(isoString) {
  if (!isoString) return ''
  return new Date(isoString).toLocaleTimeString([], {
    hour:   '2-digit',
    minute: '2-digit',
  })
}

/**
 * Format file size in bytes to a human-readable string.
 * e.g. 2097152 → "2.0 MB"
 */
export function formatFileSize(bytes) {
  if (bytes < 1024)           return `${bytes} B`
  if (bytes < 1024 * 1024)   return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/**
 * Strip the file extension from a filename for display.
 * e.g. "lecture_3_neural_nets.pdf" → "lecture_3_neural_nets"
 */
export function stripExtension(filename) {
  if (!filename) return ''
  return filename.replace(/\.[^/.]+$/, '')
}
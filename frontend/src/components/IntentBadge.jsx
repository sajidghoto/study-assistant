// frontend/src/components/IntentBadge.jsx
//
// Coloured pill showing the detected intent + confidence.
// Purely presentational — no state, no side effects.

import { INTENT_COLORS } from "../../utils/constants";
import { formatConfidence } from "../../utils/formatters";

/**
 * @param {string} intent      "answer" | "summarise" | "out-of-scope"
 * @param {number} confidence  0.0 – 1.0
 */
export default function IntentBadge({ intent, confidence }) {
  if (!intent) return null;

  const colors = INTENT_COLORS[intent] || INTENT_COLORS["out-of-scope"];

  return (
    <div
      className={`
      inline-flex items-center gap-1.5 px-2.5 py-1
      rounded-full border text-xs font-medium
      ${colors.bg} ${colors.text} ${colors.border}
    `}
    >
      {/* Pulsing dot */}
      <span className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />

      {/* Intent label */}
      <span>{colors.label}</span>

      {/* Confidence percentage */}
      {confidence !== null && confidence !== undefined && (
        <span className="opacity-60">{formatConfidence(confidence)}</span>
      )}
    </div>
  );
}

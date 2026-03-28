// frontend/src/components/SourcesPanel.jsx
//
// Collapsible panel showing retrieved source chunks.
// Renders below each assistant message.
// Each source shows: document name, similarity score, chunk text preview.

import { useState } from "react";
import {
  formatScore,
  truncateText,
  stripExtension,
} from "../../utils/formatters";

/**
 * @param {Array} sources  List of source chunk objects from the API
 */
export default function SourcesPanel({ sources }) {
  const [isOpen, setIsOpen] = useState(false);
  const [expandedIds, setExpandedIds] = useState(new Set());

  if (!sources || sources.length === 0) return null;

  // Toggle individual chunk expansion
  const toggleChunk = (chunkId) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      next.has(chunkId) ? next.delete(chunkId) : next.add(chunkId);
      return next;
    });
  };

  return (
    <div className="mt-3 border border-slate-700/50 rounded-lg overflow-hidden">
      {/* ── Toggle button ─────────────────────────────────────── */}
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className="
          w-full flex items-center justify-between
          px-3 py-2 text-xs text-slate-400
          hover:bg-slate-800/50 transition-colors
          bg-slate-800/30
        "
      >
        <div className="flex items-center gap-2">
          {/* Stack icon */}
          <svg
            className="w-3.5 h-3.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
            />
          </svg>
          <span className="font-medium">Sources ({sources.length})</span>
        </div>

        {/* Chevron */}
        <svg
          className={`w-3.5 h-3.5 transition-transform ${isOpen ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* ── Expanded content ──────────────────────────────────── */}
      {isOpen && (
        <div className="divide-y divide-slate-700/30">
          {sources.map((source, index) => {
            const isExpanded = expandedIds.has(source.chunk_id);
            const scorePercent = formatScore(source.score);
            const scoreValue = Math.round(source.score * 100);

            // Colour-code the score bar
            const barColor =
              scoreValue >= 60
                ? "bg-emerald-500"
                : scoreValue >= 30
                  ? "bg-yellow-500"
                  : "bg-red-400";

            return (
              <div
                key={source.chunk_id}
                className="px-3 py-2.5 bg-slate-900/30"
              >
                {/* Source header */}
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2 min-w-0">
                    {/* Source number */}
                    <span
                      className="
                      shrink-0 w-5 h-5 rounded-full bg-slate-700
                      flex items-center justify-center
                      text-xs text-slate-300 font-mono
                    "
                    >
                      {index + 1}
                    </span>

                    {/* Document name */}
                    <span className="text-xs text-slate-300 truncate font-medium">
                      {stripExtension(source.document_name)}
                    </span>
                  </div>

                  {/* Similarity score */}
                  <span className="shrink-0 text-xs text-slate-400 font-mono">
                    {scorePercent}
                  </span>
                </div>

                {/* Score bar */}
                <div className="h-0.5 bg-slate-700 rounded-full mb-2">
                  <div
                    className={`h-full rounded-full transition-all ${barColor}`}
                    style={{ width: `${Math.min(scoreValue, 100)}%` }}
                  />
                </div>

                {/* Chunk text preview */}
                <p className="text-xs text-slate-400 leading-relaxed">
                  {isExpanded ? source.text : truncateText(source.text, 180)}
                </p>

                {/* Show more / less toggle */}
                {source.text.length > 180 && (
                  <button
                    onClick={() => toggleChunk(source.chunk_id)}
                    className="mt-1 text-xs text-slate-500 hover:text-slate-300 transition-colors"
                  >
                    {isExpanded ? "Show less" : "Show more"}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

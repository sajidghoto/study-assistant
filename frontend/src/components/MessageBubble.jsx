// frontend/src/components/MessageBubble.jsx
//
// Renders a single message in the chat window.
// Handles both user and assistant messages.
// Assistant messages include IntentBadge + SourcesPanel.

import IntentBadge from "./IntentBadge";
import SourcesPanel from "./SourcesPanel";
import { formatTime } from "../../utils/formatters";

/**
 * @param {object} message  Message object from useChat hook
 */
export default function MessageBubble({ message }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[75%]">
          <div
            className="
            bg-indigo-600 text-white
            rounded-2xl rounded-tr-sm
            px-4 py-2.5 text-sm leading-relaxed
          "
          >
            {message.text}
          </div>
          <div className="text-right mt-1">
            <span className="text-xs text-slate-600">
              {formatTime(message.timestamp)}
            </span>
          </div>
        </div>
      </div>
    );
  }

  // ── Assistant message ───────────────────────────────────────────
  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[85%] w-full">
        {/* Intent badge + timestamp row */}
        {!message.isError && message.intent && (
          <div className="flex items-center gap-2 mb-2">
            <IntentBadge
              intent={message.intent}
              confidence={message.confidence}
            />
            <span className="text-xs text-slate-600">
              {formatTime(message.timestamp)}
            </span>
          </div>
        )}

        {/* Answer bubble */}
        <div
          className={`
          rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed
          ${
            message.isError
              ? "bg-red-500/10 border border-red-500/20 text-red-400"
              : "bg-slate-800 text-slate-200"
          }
        `}
        >
          {/* Error icon */}
          {message.isError && (
            <div className="flex items-center gap-2 mb-1.5 text-red-400">
              <svg
                className="w-4 h-4 shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              <span className="text-xs font-medium">Error</span>
            </div>
          )}

          {/* Answer text — preserve newlines from Gemini */}
          <p className="whitespace-pre-wrap">{message.answer}</p>
        </div>

        {/* Sources panel — only for non-error assistant messages */}
        {!message.isError && message.sources?.length > 0 && (
          <SourcesPanel sources={message.sources} />
        )}

        {/* Timestamp for error messages */}
        {message.isError && (
          <div className="mt-1">
            <span className="text-xs text-slate-600">
              {formatTime(message.timestamp)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

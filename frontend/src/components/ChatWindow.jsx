// frontend/src/components/ChatWindow.jsx
//
// Right panel: the full chat interface.
// Includes: message history, document filter, input box.

import { useEffect, useRef, useState } from "react";
import { useChat } from "../hooks/useChat";
import MessageBubble from "./MessageBubble";
import DocumentFilter from "./DocumentFilter";

/**
 * @param {string} sessionId
 * @param {Array}  documents   For the document filter dropdown
 */
export default function ChatWindow({ sessionId, documents }) {
  const [inputText, setInputText] = useState("");
  const [selectedDocId, setSelectedDocId] = useState(null);

  const messagesEndRef = useRef(null);

  const { messages, querying, handleQuery, clearMessages } = useChat(
    sessionId,
    selectedDocId,
  );

  // Auto-scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Reset document filter when documents change
  // (e.g., if the selected document was deleted)
  useEffect(() => {
    if (selectedDocId) {
      const stillExists = documents.some(
        (d) => d.document_id === selectedDocId,
      );
      if (!stillExists) setSelectedDocId(null);
    }
  }, [documents, selectedDocId]);

  const handleSubmit = () => {
    if (!inputText.trim() || querying) return;
    handleQuery(inputText);
    setInputText("");
  };

  const handleKeyDown = (e) => {
    // Send on Enter, newline on Shift+Enter
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const hasDocuments = documents.length > 0;

  return (
    <div className="flex flex-col h-full">
      {/* ── Chat header ─────────────────────────────────────────── */}
      <div
        className="
        px-4 py-3 border-b border-slate-700/50
        flex items-center justify-between
      "
      >
        <div>
          <h2 className="text-sm font-semibold text-slate-200">Study Chat</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {hasDocuments
              ? "Ask anything about your uploaded notes"
              : "Upload a PDF to start asking questions"}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Document filter */}
          <DocumentFilter
            documents={documents}
            selectedId={selectedDocId}
            onSelect={setSelectedDocId}
            disabled={querying}
          />

          {/* Clear chat button */}
          {messages.length > 0 && (
            <button
              onClick={clearMessages}
              className="text-xs text-slate-600 hover:text-slate-400 transition-colors px-2 py-1 rounded"
              title="Clear chat"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* ── Message history ──────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {/* Empty state */}
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center px-6">
            {hasDocuments ? (
              <>
                <div className="w-12 h-12 rounded-2xl bg-slate-800 flex items-center justify-center mb-3">
                  <svg
                    className="w-6 h-6 text-indigo-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <p className="text-sm font-medium text-slate-300 mb-1">
                  Ready to answer
                </p>
                <p className="text-xs text-slate-500 max-w-xs">
                  Ask a question, request a summary, or explore your notes.
                </p>
                {/* Example prompts */}
                <div className="mt-4 space-y-2 w-full max-w-sm">
                  {[
                    "What is the main topic of these notes?",
                    "Summarize the key concepts covered",
                    "Explain the most important definition",
                  ].map((prompt) => (
                    <button
                      key={prompt}
                      onClick={() => {
                        setInputText(prompt);
                      }}
                      className="
                        w-full text-left text-xs text-slate-400
                        bg-slate-800/50 hover:bg-slate-800
                        border border-slate-700/50 hover:border-slate-600
                        rounded-lg px-3 py-2 transition-all
                      "
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </>
            ) : (
              <>
                <div className="w-12 h-12 rounded-2xl bg-slate-800 flex items-center justify-center mb-3">
                  <svg
                    className="w-6 h-6 text-slate-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                </div>
                <p className="text-sm font-medium text-slate-400 mb-1">
                  No notes uploaded yet
                </p>
                <p className="text-xs text-slate-600">
                  Upload a PDF from the panel on the left to get started.
                </p>
              </>
            )}
          </div>
        )}

        {/* Messages */}
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {/* Thinking indicator */}
        {querying && (
          <div className="flex justify-start mb-4">
            <div className="bg-slate-800 rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
                <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
                <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" />
              </div>
            </div>
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* ── Input area ───────────────────────────────────────────── */}
      <div className="px-4 py-3 border-t border-slate-700/50">
        <div
          className={`
          flex items-end gap-2
          bg-slate-800 border rounded-2xl px-3 py-2
          transition-colors
          ${
            !hasDocuments
              ? "border-slate-700/50 opacity-50"
              : querying
                ? "border-indigo-500/30"
                : "border-slate-700 focus-within:border-indigo-500/50"
          }
        `}
        >
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              hasDocuments
                ? "Ask a question about your notes… (Enter to send)"
                : "Upload a PDF first"
            }
            disabled={!hasDocuments || querying}
            rows={1}
            className="
              flex-1 bg-transparent text-sm text-slate-200
              placeholder-slate-600 resize-none
              focus:outline-none disabled:cursor-not-allowed
              max-h-32 min-h-[1.5rem]
            "
            style={{
              // Auto-grow textarea up to max-h
              height: "auto",
              overflowY: inputText.split("\n").length > 4 ? "auto" : "hidden",
            }}
            onInput={(e) => {
              e.target.style.height = "auto";
              e.target.style.height = `${e.target.scrollHeight}px`;
            }}
          />

          {/* Send button */}
          <button
            onClick={handleSubmit}
            disabled={!hasDocuments || querying || !inputText.trim()}
            className="
              shrink-0 w-8 h-8 rounded-xl
              flex items-center justify-center
              transition-all
              bg-indigo-600 hover:bg-indigo-500
              disabled:bg-slate-700 disabled:cursor-not-allowed
            "
          >
            {querying ? (
              <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <svg
                className="w-3.5 h-3.5 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2.5}
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
            )}
          </button>
        </div>

        {/* Footer hint */}
        <p className="text-center text-xs text-slate-700 mt-2">
          Answers are grounded in your uploaded notes only
        </p>
      </div>
    </div>
  );
}

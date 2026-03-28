// frontend/src/components/FileUpload.jsx
//
// Left panel: PDF upload area + list of uploaded documents.
// Handles drag-and-drop and click-to-browse.

import { useRef } from "react";
import { useUpload } from "../hooks/useUpload";
import { formatFileSize, stripExtension } from "../../utils/formatters";

/**
 * @param {string}   sessionId
 * @param {Array}    documents        Current document list from session
 * @param {Function} onUploadSuccess  Called after upload/delete to refresh
 */
export default function FileUpload({ sessionId, documents, onUploadSuccess }) {
  const fileInputRef = useRef(null);

  const {
    uploading,
    uploadProgress,
    uploadError,
    deletingId,
    setUploadError,
    handleUpload,
    handleDelete,
    handleDrop,
    handleDragOver,
  } = useUpload(sessionId, onUploadSuccess);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) handleUpload(file);
    // Reset input so the same file can be re-uploaded after deletion
    e.target.value = "";
  };

  return (
    <div className="flex flex-col h-full">
      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="px-4 py-3 border-b border-slate-700/50">
        <h2 className="text-sm font-semibold text-slate-200">
          Study Materials
        </h2>
        <p className="text-xs text-slate-500 mt-0.5">
          {documents.length === 0
            ? "Upload your lecture notes"
            : `${documents.length} document${documents.length > 1 ? "s" : ""} loaded`}
        </p>
      </div>

      {/* ── Drop zone ──────────────────────────────────────────── */}
      <div className="px-3 pt-3">
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onClick={() => !uploading && fileInputRef.current?.click()}
          className={`
            relative border-2 border-dashed rounded-xl
            flex flex-col items-center justify-center
            gap-2 py-6 px-3 text-center
            transition-all duration-200
            ${
              uploading
                ? "border-indigo-500/50 bg-indigo-500/5 cursor-wait"
                : "border-slate-700 hover:border-indigo-500/50 hover:bg-slate-800/50 cursor-pointer"
            }
          `}
        >
          {uploading ? (
            <>
              {/* Upload progress */}
              <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
              <p className="text-xs text-indigo-400 font-medium">
                Uploading... {uploadProgress > 0 ? `${uploadProgress}%` : ""}
              </p>
              {uploadProgress > 0 && (
                <div className="w-full h-1 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-indigo-500 rounded-full transition-all"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              )}
            </>
          ) : (
            <>
              {/* Upload icon */}
              <div className="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center">
                <svg
                  className="w-5 h-5 text-slate-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                  />
                </svg>
              </div>
              <div>
                <p className="text-xs font-medium text-slate-300">
                  Drop PDF here or click to browse
                </p>
                <p className="text-xs text-slate-600 mt-0.5">
                  Max 20 MB · PDF only
                </p>
              </div>
            </>
          )}

          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            onChange={handleFileChange}
            className="hidden"
            disabled={uploading}
          />
        </div>

        {/* Error message */}
        {uploadError && (
          <div className="mt-2 flex items-start gap-2 text-xs text-red-400 bg-red-500/10 rounded-lg px-3 py-2">
            <svg
              className="w-3.5 h-3.5 shrink-0 mt-0.5"
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
            <span>{uploadError}</span>
            <button
              onClick={() => setUploadError(null)}
              className="ml-auto shrink-0 hover:text-red-300"
            >
              ×
            </button>
          </div>
        )}
      </div>

      {/* ── Document list ───────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-3 py-2 mt-1 space-y-1.5">
        {documents.length === 0 ? (
          <p className="text-xs text-slate-600 text-center py-4">
            No documents yet
          </p>
        ) : (
          documents.map((doc) => (
            <div
              key={doc.document_id}
              className="
                flex items-start gap-2.5 p-2.5
                bg-slate-800/50 rounded-lg
                border border-slate-700/30
                group
              "
            >
              {/* PDF icon */}
              <div className="shrink-0 w-7 h-7 rounded-lg bg-red-500/20 flex items-center justify-center">
                <svg
                  className="w-3.5 h-3.5 text-red-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>

              {/* Doc info */}
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-slate-300 truncate">
                  {stripExtension(doc.document_name)}
                </p>
                <p className="text-xs text-slate-600 mt-0.5">
                  {doc.chunk_count} chunks · {doc.page_count} pages
                </p>
              </div>

              {/* Delete button */}
              <button
                onClick={() => handleDelete(doc.document_id)}
                disabled={deletingId === doc.document_id}
                className="
                  shrink-0 opacity-0 group-hover:opacity-100
                  text-slate-600 hover:text-red-400
                  transition-all disabled:opacity-50
                "
                title="Remove document"
              >
                {deletingId === doc.document_id ? (
                  <div className="w-3.5 h-3.5 border border-slate-500 border-t-transparent rounded-full animate-spin" />
                ) : (
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
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                )}
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

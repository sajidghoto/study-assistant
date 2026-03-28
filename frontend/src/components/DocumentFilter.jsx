// frontend/src/components/DocumentFilter.jsx
//
// Dropdown to select which document to query.
// "All Documents" = null document_id (search across everything)
// A specific document = that document's ID is sent with the query.

import { SCOPE_ALL } from "../../utils/constants";
import { stripExtension } from "../../utils/formatters";

/**
 * @param {Array}    documents          List of DocumentInfo objects
 * @param {string|null} selectedId      Currently selected document_id
 * @param {Function} onSelect           Called with document_id or null
 * @param {boolean}  disabled           True while a query is in progress
 */
export default function DocumentFilter({
  documents,
  selectedId,
  onSelect,
  disabled,
}) {
  if (!documents || documents.length === 0) return null;

  return (
    <div className="flex items-center gap-2">
      {/* Filter icon */}
      <svg
        className="w-3.5 h-3.5 text-slate-500 shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z"
        />
      </svg>

      <select
        value={selectedId || SCOPE_ALL}
        onChange={(e) => {
          const val = e.target.value;
          onSelect(val === SCOPE_ALL ? null : val);
        }}
        disabled={disabled}
        className="
          text-xs bg-slate-800 text-slate-300
          border border-slate-700 rounded-lg
          px-2.5 py-1.5 pr-7
          focus:outline-none focus:border-indigo-500
          disabled:opacity-50 disabled:cursor-not-allowed
          appearance-none cursor-pointer
          bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 fill=%22none%22 viewBox=%220 0 20 20%22%3E%3Cpath stroke=%22%236b7280%22 stroke-linecap=%22round%22 stroke-linejoin=%22round%22 stroke-width=%221.5%22 d=%22M6 8l4 4 4-4%22/%3E%3C/svg%3E')]
          bg-[position:right_4px_center] bg-[size:16px] bg-no-repeat
        "
      >
        <option value={SCOPE_ALL}>All Documents</option>
        {documents.map((doc) => (
          <option key={doc.document_id} value={doc.document_id}>
            {stripExtension(doc.document_name)}
          </option>
        ))}
      </select>
    </div>
  );
}

// frontend/src/hooks/useUpload.js
//
// Manages PDF upload state:
//   - Validates file before sending
//   - Tracks upload progress
//   - Calls refreshSession after success

import { useState, useCallback } from "react";
import { uploadPDF, deleteDocument } from "../api/upload";
import {
  MAX_FILE_SIZE_MB,
  ACCEPTED_MIME,
  ACCEPTED_EXT,
} from "../../utils/constants";

/**
 * @param {string}   sessionId
 * @param {Function} onUploadSuccess  Called after a successful upload
 *                                    to trigger session refresh
 */
export function useUpload(sessionId, onUploadSuccess) {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState(null);
  const [deletingId, setDeletingId] = useState(null); // doc being deleted

  // ── Client-side file validation ─────────────────────────────────
  // We validate before sending to give instant feedback.
  // The backend also validates — defense in depth.
  const validateFile = useCallback((file) => {
    if (!file) {
      return "No file selected.";
    }

    const isPDF =
      file.type === ACCEPTED_MIME ||
      file.name.toLowerCase().endsWith(ACCEPTED_EXT);
    if (!isPDF) {
      return "Only PDF files are accepted.";
    }

    const sizeMB = file.size / (1024 * 1024);
    if (sizeMB > MAX_FILE_SIZE_MB) {
      return `File is too large (${sizeMB.toFixed(1)} MB). Maximum is ${MAX_FILE_SIZE_MB} MB.`;
    }

    return null; // null means valid
  }, []);

  // ── Upload handler ──────────────────────────────────────────────
  const handleUpload = useCallback(
    async (file) => {
      if (!sessionId) return;

      // Validate first
      const validationError = validateFile(file);
      if (validationError) {
        setUploadError(validationError);
        return;
      }

      setUploading(true);
      setUploadError(null);
      setUploadProgress(0);

      try {
        await uploadPDF(sessionId, file, (percent) => {
          setUploadProgress(percent);
        });

        // Notify parent to refresh document list
        if (onUploadSuccess) await onUploadSuccess();
      } catch (err) {
        // Extract structured error message from API response
        const apiMessage = err.response?.data?.error?.message;
        setUploadError(apiMessage || "Upload failed. Please try again.");
      } finally {
        setUploading(false);
        setUploadProgress(0);
      }
    },
    [sessionId, validateFile, onUploadSuccess],
  );

  // ── Delete handler ──────────────────────────────────────────────
  const handleDelete = useCallback(
    async (documentId) => {
      if (!sessionId) return;

      setDeletingId(documentId);

      try {
        await deleteDocument(sessionId, documentId);
        if (onUploadSuccess) await onUploadSuccess();
      } catch (err) {
        const apiMessage = err.response?.data?.error?.message;
        setUploadError(apiMessage || "Failed to remove document.");
      } finally {
        setDeletingId(null);
      }
    },
    [sessionId, onUploadSuccess],
  );

  // ── Drag and drop handler ───────────────────────────────────────
  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file) handleUpload(file);
    },
    [handleUpload],
  );

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
  }, []);

  return {
    uploading,
    uploadProgress,
    uploadError,
    deletingId,
    setUploadError,
    handleUpload,
    handleDelete,
    handleDrop,
    handleDragOver,
  };
}

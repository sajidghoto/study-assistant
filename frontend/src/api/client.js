// frontend/src/api/client.js
//
// Single Axios instance used by all API modules.
// Configure once here — never create axios instances elsewhere.

import axios from "axios";
import { API_BASE } from "../../utils/constants";

const client = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
  // 30 second timeout — Gemini can take up to 15s on heavy queries
  timeout: 30000,
});

// ── Response interceptor ───────────────────────────────────────────
// Runs on every response before it reaches the calling code.
// On error: logs to console in development, re-throws for
// individual API functions to handle with specific messages.
client.interceptors.response.use(
  // Success: pass through unchanged
  (response) => response,

  // Error: log and re-throw
  (error) => {
    // Extract the structured error from our API envelope if available
    const apiError = error.response?.data?.error;

    if (apiError) {
      // Our backend returned a structured error — log it clearly
      console.error(
        `[API Error] ${apiError.code}: ${apiError.message}`,
        "\nDetail:",
        apiError.detail,
      );
    } else if (error.code === "ECONNABORTED") {
      console.error("[API Error] Request timed out after 30s");
    } else {
      console.error("[API Error] Unexpected error:", error.message);
    }

    // Always re-throw — let the calling hook decide how to display the error
    return Promise.reject(error);
  },
);

export default client;

import axios from 'axios'

/**
 * Shared Axios instance for all API calls.
 *
 * Base URL is read from the Vite environment variable VITE_API_BASE_URL
 * (defaults to empty string so requests go to the same origin via the Vite proxy).
 *
 * SECURITY NOTE — VITE_API_KEY:
 * VITE_* variables are bundled into the frontend JavaScript at build time and are
 * visible to anyone who inspects the browser bundle.  They are NOT suitable for
 * production secrets.  VITE_API_KEY is used here only for development/demo
 * convenience.  In a production deployment requiring authentication, use a
 * backend session/token exchange instead of a shared static key.
 */
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '',
  timeout: 15_000,
  headers: {
    'Content-Type': 'application/json',
    // VITE_API_KEY — development/demo only; not a production secret mechanism
    ...(import.meta.env.VITE_API_KEY
      ? { 'X-API-Key': import.meta.env.VITE_API_KEY }
      : {}),
  },
})

// Response interceptor — log errors in development
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (import.meta.env.DEV) {
      console.error('[INDUSTRIA-X API error]', error?.response?.status, error?.message)
    }
    return Promise.reject(error)
  },
)

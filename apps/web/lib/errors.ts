/**
 * API error handling utilities.
 *
 * Extracts structured error messages from the AgentSetu API's
 * standard error envelope: { error: { code, message, request_id, details } }
 *
 * SECURITY: Never expose raw error details to the user in production.
 * The extracted message is always the server's human-readable string.
 */

import { AxiosError } from 'axios'

export interface ApiErrorDetail {
  code: string
  message: string
  request_id?: string
  details?: Record<string, unknown>
}

/**
 * Extract a human-readable error message from an Axios error.
 *
 * Handles:
 *   - Standard error envelope: { error: { code, message } }
 *   - Legacy detail string: { detail: "..." }
 *   - Legacy detail object: { detail: { error: { message } } }
 *   - Network errors (no response)
 *   - Unknown shapes (fallback message)
 */
export function extractErrorMessage(err: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (!err) return fallback

  if (err instanceof AxiosError) {
    const data = err.response?.data

    // Standard error envelope
    if (data?.error?.message) {
      return data.error.message
    }

    // Legacy: { detail: { error: { message } } }
    if (typeof data?.detail === 'object' && data.detail?.error?.message) {
      return data.detail.error.message
    }

    // Legacy: { detail: "string" }
    if (typeof data?.detail === 'string') {
      return data.detail
    }

    // HTTP status fallbacks
    const status = err.response?.status
    if (status === 401) return 'Your session has expired. Please sign in again.'
    if (status === 403) return 'You do not have permission to perform this action.'
    if (status === 404) return 'The requested resource was not found.'
    if (status === 429) return 'Too many requests. Please wait a moment and try again.'
    if (status && status >= 500) return 'A server error occurred. Please try again later.'

    // Network error
    if (err.code === 'ERR_NETWORK' || !err.response) {
      return 'Unable to connect to the server. Check your connection and try again.'
    }
  }

  if (err instanceof Error) {
    return err.message
  }

  return fallback
}

/**
 * Extract the full structured error detail from an Axios error.
 */
export function extractApiError(err: unknown): ApiErrorDetail | null {
  if (err instanceof AxiosError && err.response?.data?.error) {
    return err.response.data.error as ApiErrorDetail
  }
  return null
}

/**
 * Check if an error is a specific API error code.
 */
export function isApiErrorCode(err: unknown, code: string): boolean {
  const detail = extractApiError(err)
  return detail?.code === code
}

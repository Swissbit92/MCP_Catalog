/**
 * API service barrel — all functions re-exported from domain modules.
 *
 * Import from this file as before:
 *   import { fetchSessions, sendMessageToSession } from '../services/api'
 *
 * For new code, prefer the focused domain imports:
 *   import { fetchSessions } from '../services/api/sessions'
 */
export * from './api/index'

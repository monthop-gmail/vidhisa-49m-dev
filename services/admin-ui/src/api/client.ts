import createClient, { type Middleware } from 'openapi-fetch'
import type { paths } from './schema'
import { clearSession, getToken } from '../lib/auth'

// OpenAPI paths already include the /api prefix, so baseUrl is just the origin.
// In dev, Vite proxies /api/* to the backend (see vite.config.ts).
const baseUrl = import.meta.env.VITE_API_URL ?? ''

const authMiddleware: Middleware = {
  onRequest({ request }) {
    const token = getToken()
    if (token) request.headers.set('Authorization', `Bearer ${token}`)
    return request
  },
  onResponse({ response }) {
    if (response.status === 401) clearSession()
    return response
  },
}

export const api = createClient<paths>({ baseUrl })
api.use(authMiddleware)

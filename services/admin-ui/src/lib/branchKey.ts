/**
 * Encode/decode branch key — short obfuscated token in URL.
 * MOCKUP ONLY: secret hardcoded; in production this becomes branches.view_secret in DB.
 */

const SECRET = 'vidhisa-2569-me'

export function encodeBranchKey(branchId: string): string {
  return btoa(`${branchId}.${SECRET}`).replace(/=+$/, '').replace(/\+/g, '-').replace(/\//g, '_')
}

export function decodeBranchKey(key: string): string | null {
  try {
    const padded = key.replace(/-/g, '+').replace(/_/g, '/')
    const decoded = atob(padded)
    const [branchId, secret] = decoded.split('.')
    if (secret !== SECRET || !branchId) return null
    return branchId
  } catch {
    return null
  }
}

const STORAGE_PREFIX = 'vidhisa.me.'

export function getRememberedParticipant(branchId: string): number | null {
  try {
    const v = localStorage.getItem(STORAGE_PREFIX + branchId)
    return v ? Number(v) : null
  } catch {
    return null
  }
}

export function rememberParticipant(branchId: string, participantId: number): void {
  localStorage.setItem(STORAGE_PREFIX + branchId, String(participantId))
}

export function forgetParticipant(branchId: string): void {
  localStorage.removeItem(STORAGE_PREFIX + branchId)
}

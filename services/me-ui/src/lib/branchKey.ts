/**
 * Branch key helpers — split URL `/br/{branch_id}-{secret}` into 2 parts.
 * No decode needed since secret lives in DB; we just verify via API.
 */

export type BranchKey = { branchId: string; secret: string }

/** Split key like "B012-A3F9X2" into branchId + secret. Returns null if malformed. */
export function parseBranchKey(key: string): BranchKey | null {
  const m = /^(B\d{3})-([0-9A-HJKMNP-TV-Z]{6})$/.exec(key)
  if (!m) return null
  return { branchId: m[1], secret: m[2] }
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

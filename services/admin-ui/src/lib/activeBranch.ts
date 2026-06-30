/**
 * Active Branch — สำหรับ multi-branch admin
 *
 * - Central admin: ใช้ค่าว่าง (=ไม่ filter / เห็นทุกสาขา)
 * - Branch admin 1 สาขา: lock เป็น user.branch_id
 * - Branch admin หลายสาขา: เลือกได้จาก dropdown ใน navbar (เก็บใน localStorage)
 */

import { useSyncExternalStore } from 'react'
import { getAuth } from './auth'

const STORAGE_KEY = 'vidhisa.active_branch_id'

function read(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) ?? ''
  } catch {
    return ''
  }
}

let current = read()
const listeners = new Set<() => void>()

function emit() {
  listeners.forEach((fn) => fn())
}

export function getActiveBranch(): string {
  return current
}

export function setActiveBranch(branchId: string): void {
  current = branchId
  if (branchId) localStorage.setItem(STORAGE_KEY, branchId)
  else localStorage.removeItem(STORAGE_KEY)
  emit()
}

function subscribe(fn: () => void): () => void {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

/**
 * Hook to read current active branch.
 * - Central admin: returns '' (no filter)
 * - Single-branch user: returns their branch_id (auto-locked)
 * - Multi-branch user: returns stored active branch (default first in branch_ids)
 */
export function useActiveBranch(): string {
  const stored = useSyncExternalStore(subscribe, getActiveBranch, getActiveBranch)
  const { user } = getAuth()
  if (!user) return ''
  if (user.role === 'central_admin') return stored  // can be filtered too
  const ids = user.branch_ids && user.branch_ids.length > 0 ? user.branch_ids : (user.branch_id ? [user.branch_id] : [])
  if (ids.length === 0) return ''
  if (ids.length === 1) return ids[0]  // locked
  // multi-branch: use stored if valid, else first
  if (stored && ids.includes(stored)) return stored
  return ids[0]
}

/** Whether user is locked to 1 branch (UI should disable switcher) */
export function isBranchLocked(): boolean {
  const { user } = getAuth()
  if (!user || user.role === 'central_admin') return false
  const ids = user.branch_ids && user.branch_ids.length > 0 ? user.branch_ids : (user.branch_id ? [user.branch_id] : [])
  return ids.length === 1
}

import { useEffect, useState } from 'react'

export type Pagination = {
  page: number
  pageSize: number
  offset: number
  // Probe size: fetch this many items from the API; if you get back > pageSize, there's a next page
  probeLimit: number
  setPage: (p: number) => void
  reset: () => void
}

/**
 * Page state with hasNext probe (no total count from API).
 * Pass `resetKey` (e.g. JSON of filters) — when it changes, page resets to 0.
 */
export function usePagination(pageSize = 50, resetKey?: string): Pagination {
  const [page, setPage] = useState(0)

  useEffect(() => {
    setPage(0)
  }, [resetKey])

  return {
    page,
    pageSize,
    offset: page * pageSize,
    probeLimit: pageSize + 1,
    setPage,
    reset: () => setPage(0),
  }
}

/**
 * Slice the probe response: return the visible page (≤ pageSize) and whether next exists.
 */
export function splitPage<T>(rows: T[], pageSize: number): { visible: T[]; hasNext: boolean } {
  if (rows.length > pageSize) {
    return { visible: rows.slice(0, pageSize), hasNext: true }
  }
  return { visible: rows, hasNext: false }
}

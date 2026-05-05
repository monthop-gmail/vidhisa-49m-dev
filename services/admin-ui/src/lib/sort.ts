import { useState } from 'react'

export type SortDir = 'asc' | 'desc'
export type SortState<K extends string = string> = { key: K; dir: SortDir } | null

export type UseSortableOptions<T, K extends string> = {
  defaultSort?: SortState<K>
  /** Custom value extractor — return a string or number to compare. Falsy → empty string. */
  getValue?: (row: T, key: K) => unknown
}

export function useSortable<T, K extends string = string>({
  defaultSort = null,
  getValue,
}: UseSortableOptions<T, K> = {}) {
  const [sort, setSort] = useState<SortState<K>>(defaultSort)

  function toggleSort(key: K) {
    setSort((prev) => {
      if (!prev || prev.key !== key) return { key, dir: 'asc' }
      if (prev.dir === 'asc') return { key, dir: 'desc' }
      return null // cycle back to unsorted
    })
  }

  function sortRows(rows: T[]): T[] {
    if (!sort) return rows
    const acc = (r: T): unknown => (getValue ? getValue(r, sort.key) : (r as Record<string, unknown>)[sort.key])
    const copy = rows.slice()
    copy.sort((a, b) => {
      const av = acc(a)
      const bv = acc(b)
      const cmp = compareValues(av, bv)
      return sort.dir === 'asc' ? cmp : -cmp
    })
    return copy
  }

  return { sort, setSort, toggleSort, sortRows }
}

function compareValues(a: unknown, b: unknown): number {
  // null/undefined sort last
  const aNull = a == null || a === ''
  const bNull = b == null || b === ''
  if (aNull && bNull) return 0
  if (aNull) return 1
  if (bNull) return -1

  if (typeof a === 'number' && typeof b === 'number') return a - b
  const an = typeof a === 'string' ? Number(a) : NaN
  const bn = typeof b === 'string' ? Number(b) : NaN
  if (!Number.isNaN(an) && !Number.isNaN(bn)) return an - bn

  return String(a).localeCompare(String(b), 'th')
}

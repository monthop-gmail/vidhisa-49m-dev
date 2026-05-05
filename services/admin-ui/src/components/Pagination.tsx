import { Button } from './ui'

export function Pagination({
  page,
  hasNext,
  onChange,
  visibleCount,
  pageSize,
}: {
  page: number
  hasNext: boolean
  onChange: (p: number) => void
  visibleCount: number
  pageSize: number
}) {
  const start = page * pageSize + 1
  const end = page * pageSize + visibleCount
  return (
    <div className="flex items-center justify-between gap-3 text-sm text-slate-600">
      <span>
        แสดง <strong className="text-slate-900">{start.toLocaleString()}</strong>–
        <strong className="text-slate-900">{end.toLocaleString()}</strong>
        {!hasNext && page === 0 ? '' : ` · หน้า ${page + 1}`}
      </span>
      <div className="flex gap-2">
        <Button variant="secondary" size="sm" onClick={() => onChange(page - 1)} disabled={page === 0}>
          ← Prev
        </Button>
        <Button variant="secondary" size="sm" onClick={() => onChange(page + 1)} disabled={!hasNext}>
          Next →
        </Button>
      </div>
    </div>
  )
}

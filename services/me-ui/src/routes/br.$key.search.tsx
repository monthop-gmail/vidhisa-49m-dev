import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { parseBranchKey, rememberParticipant } from '../lib/branchKey'

export const Route = createFileRoute('/br/$key/search')({
  component: SearchPage,
})

type SearchHit = {
  id: number
  prefix: string | null
  first_name: string
  last_name: string
  member_code: string | null
}

function SearchPage() {
  const { key } = Route.useParams()
  const navigate = useNavigate()
  const parsed = parseBranchKey(key)
  const [q, setQ] = useState('')
  const [debouncedQ, setDebouncedQ] = useState('')

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q.trim()), 250)
    return () => clearTimeout(t)
  }, [q])

  const { data, isLoading } = useQuery({
    queryKey: ['branch-view-search', parsed?.branchId, parsed?.secret, debouncedQ],
    queryFn: async () => {
      if (!parsed || !debouncedQ) return [] as SearchHit[]
      const url = `/api/branch-view/${parsed.branchId}/${parsed.secret}/participants?q=${encodeURIComponent(debouncedQ)}`
      const res = await fetch(url)
      if (!res.ok) throw new Error(String(res.status))
      return (await res.json()) as SearchHit[]
    },
    enabled: Boolean(parsed) && debouncedQ.length > 0,
  })

  const filtered = data ?? []

  function pick(p: SearchHit) {
    if (!parsed) return
    rememberParticipant(parsed.branchId, p.id)
    navigate({ to: '/br/$key/me/$participantId', params: { key, participantId: String(p.id) } })
  }

  if (!parsed) return null

  return (
    <div className="min-h-screen p-4 sm:p-6 max-w-md mx-auto">
      <div className="mb-6 text-center">
        <div className="text-sm text-slate-500">สาขา {parsed.branchId}</div>
        <h1 className="text-2xl font-bold text-slate-900 mt-1">ค้นหาชื่อของคุณ</h1>
        <p className="text-slate-500 text-sm mt-2">พิมพ์ชื่อหรือนามสกุลของคุณ แล้วกดเลือก</p>
      </div>

      <input
        type="text"
        autoFocus
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="พิมพ์ชื่อ…"
        className="w-full px-4 py-3 text-lg bg-white border-2 border-slate-300 rounded-xl focus:outline-none focus:border-blue-500"
      />

      <div className="mt-2 text-xs text-slate-400 text-center">
        {!debouncedQ
          ? 'พิมพ์ชื่อเพื่อค้นหา'
          : isLoading
            ? 'กำลังค้นหา…'
            : `พบ ${filtered.length} รายการ`}
      </div>

      <div className="mt-4 grid gap-2">
        {filtered.map((p) => (
          <button
            key={p.id}
            onClick={() => pick(p)}
            className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-left hover:border-blue-500 hover:bg-blue-50 transition active:bg-blue-100"
          >
            <div className="text-base font-medium text-slate-900">
              {p.prefix ?? ''} {p.first_name} {p.last_name}
            </div>
            {p.member_code ? <div className="text-xs text-slate-500 mt-0.5">รหัส {p.member_code}</div> : null}
          </button>
        ))}
        {debouncedQ && filtered.length === 0 && !isLoading && (
          <div className="text-center text-slate-500 py-8">ไม่พบรายชื่อ — ลองค้นด้วยชื่ออื่น</div>
        )}
      </div>
    </div>
  )
}

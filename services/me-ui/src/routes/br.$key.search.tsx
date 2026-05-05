import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { api } from '../api/client'
import { decodeBranchKey, rememberParticipant } from '../lib/branchKey'

export const Route = createFileRoute('/br/$key/search')({
  component: SearchPage,
})

function SearchPage() {
  const { key } = Route.useParams()
  const navigate = useNavigate()
  const branchId = decodeBranchKey(key)
  const [q, setQ] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['participants', branchId],
    queryFn: async () => {
      if (!branchId) return []
      const { data, error } = await api.GET('/api/participants', {
        params: { query: { branch_id: branchId, limit: 1000 } },
      })
      if (error) throw error
      return ((data ?? []) as Array<Record<string, unknown>>).filter((p) => p.status === 'approved')
    },
    enabled: Boolean(branchId),
  })

  const all = data ?? []
  const filtered = useMemo(() => {
    if (!q.trim()) return all.slice(0, 0) // empty until typed
    const ql = q.toLowerCase().trim()
    return all
      .filter((p) =>
        `${p.prefix ?? ''} ${p.first_name ?? ''} ${p.last_name ?? ''} ${p.member_code ?? ''}`
          .toLowerCase()
          .includes(ql),
      )
      .slice(0, 30)
  }, [q, all])

  function pick(p: Record<string, unknown>) {
    if (!branchId) return
    const id = Number(p.id)
    rememberParticipant(branchId, id)
    navigate({ to: '/br/$key/me/$participantId', params: { key, participantId: String(id) } })
  }

  if (!branchId) return null

  return (
    <div className="min-h-screen p-4 sm:p-6 max-w-md mx-auto">
      <div className="mb-6 text-center">
        <div className="text-sm text-slate-500">สาขา {branchId}</div>
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
        {isLoading ? 'กำลังโหลด…' : `${all.length} คนในสาขา · พิมพ์เพื่อค้นหา`}
      </div>

      <div className="mt-4 grid gap-2">
        {filtered.map((p) => (
          <button
            key={String(p.id)}
            onClick={() => pick(p)}
            className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-left hover:border-blue-500 hover:bg-blue-50 transition active:bg-blue-100"
          >
            <div className="text-base font-medium text-slate-900">
              {String(p.prefix ?? '')} {String(p.first_name ?? '')} {String(p.last_name ?? '')}
            </div>
            {p.member_code ? <div className="text-xs text-slate-500 mt-0.5">รหัส {String(p.member_code)}</div> : null}
          </button>
        ))}
        {q.trim() && filtered.length === 0 && !isLoading && (
          <div className="text-center text-slate-500 py-8">ไม่พบรายชื่อ — ลองค้นด้วยชื่ออื่น</div>
        )}
      </div>
    </div>
  )
}

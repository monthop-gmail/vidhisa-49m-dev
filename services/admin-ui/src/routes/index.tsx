import { createFileRoute, Link } from '@tanstack/react-router'
import { useQueries, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../lib/auth'
import { useActiveBranch } from '../lib/activeBranch'
import { ParticipantDetailModal } from '../components/DetailDrawer'
import {
  Card,
  CardBody,
  EmptyState,
  ErrorMessage,
  LoadingState,
  PageHeading,
  Table,
  Td,
  Th,
  Thead,
  Tr,
} from '../components/ui'

export const Route = createFileRoute('/')({
  component: DashboardPage,
})

function DashboardPage() {
  const { user } = useAuth()
  const activeBranch = useActiveBranch()
  // branch_admin → ใช้ active branch (จาก switcher) สำหรับ multi-branch หรือ branch_id เดิมสำหรับ single-branch
  if (user?.role === 'branch_admin') {
    const focus = activeBranch || user.branch_id
    if (focus) return <BranchDashboard key={focus} branchId={focus} />
  }
  // central admin: ถ้าเลือกสาขา → focus เป็น branch dashboard, ไม่เลือก → central
  if (user?.role === 'central_admin' && activeBranch) {
    return <BranchDashboard key={activeBranch} branchId={activeBranch} />
  }
  return <CentralDashboard />
}

// ─── Central admin: project-wide ─────────────────────────────────

function CentralDashboard() {
  const totalQ = useQuery({
    queryKey: ['stats', 'total'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/stats/total')
      if (error) throw error
      return data
    },
  })
  const projectionQ = useQuery({
    queryKey: ['projection'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/projection')
      if (error) throw error
      return data
    },
  })
  const leaderboardQ = useQuery({
    queryKey: ['leaderboard', 'branch'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/leaderboard', {
        params: { query: { type: 'branch', limit: 5 } },
      })
      if (error) throw error
      return data
    },
  })

  const total = (totalQ.data ?? {}) as Record<string, unknown>
  const projection = (projectionQ.data ?? {}) as Record<string, unknown>
  const leaderboard = (leaderboardQ.data ?? []) as Array<Record<string, unknown>>
  const pct = projection.target_minutes
    ? `${(((Number(total.total_minutes) || 0) / Number(projection.target_minutes)) * 100).toFixed(2)}%`
    : '—'

  return (
    <div className="grid gap-6">
      <PageHeading title="Central Dashboard" subtitle="ภาพรวมโครงการทั้งหมด" />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Kpi label="ยอดรวมนาที" value={fmt(total.total_minutes)} />
        <Kpi label="Records" value={fmt(total.total_records)} />
        <Kpi label="สาขาที่บันทึก" value={fmt(total.total_branches)} sub={`${fmt(total.total_orgs)} orgs`} />
        <Kpi label="เป้า 49M" value={pct} sub={projection.deadline ? `deadline ${String(projection.deadline)}` : undefined} />
      </div>

      <Card>
        <CardBody>
          <h2 className="text-base font-semibold text-slate-900 mb-3">Branch Leaderboard (top 5)</h2>
          <Table>
            <Thead>
              <Tr>
                <Th>#</Th>
                <Th>Branch</Th>
                <Th align="right">นาที</Th>
              </Tr>
            </Thead>
            <tbody>
              {leaderboard.map((b) => (
                <Tr key={String(b.branch_id)}>
                  <Td className="font-semibold text-slate-700 w-12">{String(b.rank)}</Td>
                  <Td>
                    <code className="text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded mr-2">{String(b.branch_id)}</code>
                    {String(b.branch_name)}
                  </Td>
                  <Td align="right">{fmt(b.minutes)}</Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        </CardBody>
      </Card>

      <Card>
        <CardBody>
          <h2 className="text-base font-semibold text-slate-900 mb-3">Projection</h2>
          <pre className="bg-slate-50 border border-slate-200 rounded-md p-3 text-xs whitespace-pre-wrap">
            {JSON.stringify(projection, null, 2)}
          </pre>
        </CardBody>
      </Card>
    </div>
  )
}

// ─── Branch admin: scoped to their branch ────────────────────────

function BranchDashboard({ branchId }: { branchId: string }) {
  const [detailId, setDetailId] = useState<number | null>(null)
  const queries = useQueries({
    queries: [
      {
        queryKey: ['branch', branchId],
        queryFn: async () => {
          const { data, error } = await api.GET('/api/branches/{branch_id}', {
            params: { path: { branch_id: branchId } },
          })
          if (error) throw error
          return data
        },
      },
      {
        queryKey: ['records', branchId, 'all'],
        queryFn: async () => {
          const { data, error } = await api.GET('/api/records', {
            params: { query: { branch_id: branchId, limit: 10000 } },
          })
          if (error) throw error
          return data
        },
      },
      {
        queryKey: ['participants', branchId],
        queryFn: async () => {
          const { data, error } = await api.GET('/api/participants', {
            params: { query: { branch_id: branchId, limit: 5000 } },
          })
          if (error) throw error
          return data
        },
      },
      {
        queryKey: ['organizations', branchId, 'list'],
        queryFn: async () => {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const { data, error } = await api.GET('/api/organizations', {
            params: { query: { branch_id: branchId, limit: 500 } as any },
          })
          if (error) throw error
          return data
        },
      },
      {
        queryKey: ['branch-pending', branchId],
        queryFn: async () => {
          const { data, error } = await api.GET('/api/branch/{branch_id}/pending', {
            params: { path: { branch_id: branchId } },
          })
          if (error) throw error
          return data
        },
      },
      {
        queryKey: ['leaderboard', 'branch'],
        queryFn: async () => {
          const { data, error } = await api.GET('/api/leaderboard', {
            params: { query: { type: 'branch', limit: 100 } },
          })
          if (error) throw error
          return data
        },
      },
    ],
  })

  const [branchQ, recordsQ, participantsQ, orgsQ, pendingQ, leaderboardQ] = queries
  const branch = (branchQ.data ?? {}) as Record<string, unknown>
  const records = (recordsQ.data ?? []) as Array<Record<string, unknown>>
  const participantsAll = (participantsQ.data ?? []) as Array<Record<string, unknown>>
  // นับเฉพาะ approved (ไม่รวม rejected/pending)
  const participants = participantsAll.filter((p) => p.status === 'approved')
  const orgs = (orgsQ.data ?? []) as Array<Record<string, unknown>>
  const orgsActive = orgs.filter((o) => Number(o.total_records ?? 0) > 0)
  const pending = (pendingQ.data ?? []) as Array<Record<string, unknown>>
  const leaderboard = (leaderboardQ.data ?? []) as Array<Record<string, unknown>>

  // ยอดรวมนาที: ใช้ค่าจาก /api/branches/{id} (filter org_id LIKE '%-00' ตาม business rule)
  // ไม่ใช้ records.sum() เพราะจะรวมนาทีขององค์กรภายนอกด้วย → ไม่ตรงกับหน้าอื่น
  const totalMinutes = Number(branch.total_minutes ?? 0)
  const approvedCount = records.filter((r) => r.status === 'approved').length
  const pendingCount = pending.length
  const myRank = leaderboard.find((b) => String(b.branch_id) === branchId)?.rank as number | undefined

  const byDate = new Map<string, number>()
  for (const r of records) {
    const d = String(r.date ?? '')
    if (!d) continue
    byDate.set(d, (byDate.get(d) ?? 0) + Number(r.minutes ?? 0))
  }
  const days = Array.from(byDate.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .slice(-14)

  const byParticipant = new Map<number, { minutes: number; count: number }>()
  for (const r of records) {
    if (r.participant_id == null) continue
    const id = Number(r.participant_id)
    const cur = byParticipant.get(id) ?? { minutes: 0, count: 0 }
    cur.minutes += Number(r.minutes ?? 0)
    cur.count += 1
    byParticipant.set(id, cur)
  }
  const topParticipants = Array.from(byParticipant.entries())
    .map(([id, v]) => {
      const p = participants.find((x) => Number(x.id) === id)
      return {
        id,
        name: p ? `${p.first_name ?? ''} ${p.last_name ?? ''}`.trim() : `#${id}`,
        minutes: v.minutes,
        count: v.count,
      }
    })
    .sort((a, b) => b.minutes - a.minutes)
    .slice(0, 5)

  if (queries.some((q) => q.isLoading)) return <LoadingState />
  const firstError = queries.find((q) => q.error)?.error
  if (firstError) return <ErrorMessage>{String(firstError)}</ErrorMessage>

  return (
    <div className="grid gap-6">
      <PageHeading
        title={String(branch.name ?? branchId)}
        subtitle={
          <span className="flex items-center gap-2">
            <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">{branchId}</code>
            <span>{String(branch.province ?? '')}</span>
            {myRank && <span className="text-blue-700">· อันดับ #{myRank} จาก {leaderboard.length}</span>}
          </span>
        }
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Kpi label="ยอดรวมนาที" value={fmt(totalMinutes)} sub={`${approvedCount} approved records`} />
        <Kpi
          label="รออนุมัติ"
          value={fmt(pendingCount)}
          sub={pendingCount > 0 ? <Link to="/approve" className="text-amber-700 hover:underline">→ ไปอนุมัติ</Link> : 'ไม่มีค้าง'}
          highlight={pendingCount > 0}
        />
        <Kpi
          label="Participants"
          value={fmt(participants.length)}
          sub={
            <span className="flex items-center gap-2">
              <span className="text-slate-500">approved</span>
              <Link to="/participants" className="text-blue-600 hover:underline">
                ดูทั้งหมด
              </Link>
            </span>
          }
        />
        <Kpi
          label="Organizations"
          value={fmt(orgs.length)}
          sub={
            <span className="flex items-center gap-2">
              <span className="text-slate-500">{orgsActive.length} มี records</span>
              <Link to="/organizations" className="text-blue-600 hover:underline">
                ดูทั้งหมด
              </Link>
            </span>
          }
        />
      </div>

      <Card>
        <CardBody>
          <h2 className="text-base font-semibold text-slate-900 mb-3">ยอดรายวัน ({days.length} วันล่าสุด)</h2>
          {days.length === 0 ? <EmptyState>ยังไม่มีข้อมูล</EmptyState> : <DailyBars data={days} />}
        </CardBody>
      </Card>

      <Card>
        <CardBody>
          <h2 className="text-base font-semibold text-slate-900 mb-3">Top 5 ผู้เข้าร่วมในสาขา</h2>
          {topParticipants.length === 0 ? (
            <EmptyState>ยังไม่มีข้อมูล</EmptyState>
          ) : (
            <Table>
              <Thead>
                <Tr>
                  <Th>#</Th>
                  <Th>ชื่อ</Th>
                  <Th align="right">ครั้ง</Th>
                  <Th align="right">นาที</Th>
                </Tr>
              </Thead>
              <tbody>
                {topParticipants.map((p, i) => (
                  <Tr key={p.id}>
                    <Td className="w-12 font-semibold text-slate-700">{i + 1}</Td>
                    <Td>
                      <button
                        onClick={() => setDetailId(p.id)}
                        className="text-blue-600 hover:underline text-left"
                      >
                        {p.name}
                      </button>
                    </Td>
                    <Td align="right">{p.count}</Td>
                    <Td align="right">{fmt(p.minutes)}</Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          )}
        </CardBody>
      </Card>

      <ParticipantDetailModal participantId={detailId} onClose={() => setDetailId(null)} />
    </div>
  )
}

// ─── Reusable bits ────────────────────────────────────────────────

function DailyBars({ data }: { data: Array<[string, number]> }) {
  const max = Math.max(1, ...data.map(([, v]) => v))
  const W = 760
  const H = 140
  const barW = Math.max(8, Math.floor(W / data.length) - 6)
  return (
    <div className="overflow-x-auto">
      <svg width={W} height={H + 28} className="block max-w-full">
        {data.map(([date, v], i) => {
          const x = i * (barW + 6)
          const h = (v / max) * H
          const y = H - h
          return (
            <g key={date}>
              <rect x={x} y={y} width={barW} height={h} className="fill-blue-500" rx={3} />
              <text x={x + barW / 2} y={y - 3} textAnchor="middle" fontSize="10" className="fill-slate-700">
                {v}
              </text>
              <text x={x + barW / 2} y={H + 14} textAnchor="middle" fontSize="9" className="fill-slate-400">
                {date.slice(5)}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

function Kpi({
  label,
  value,
  sub,
  highlight,
}: {
  label: string
  value: React.ReactNode
  sub?: React.ReactNode
  highlight?: boolean
}) {
  return (
    <div
      className={`border rounded-lg p-4 shadow-sm ${highlight ? 'border-amber-300 bg-amber-50' : 'border-slate-200 bg-white'}`}
    >
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-3xl font-bold text-slate-900 mt-1 tabular-nums">{value}</div>
      {sub != null && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
    </div>
  )
}

function fmt(v: unknown): string {
  const n = typeof v === 'number' ? v : Number(v)
  return Number.isFinite(n) ? n.toLocaleString() : '—'
}

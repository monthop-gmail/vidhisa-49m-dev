import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../lib/auth'
import { useActiveBranch, isBranchLocked } from '../lib/activeBranch'
import {
  useApproveOrg,
  useApproveParticipant,
  useApproveRecord,
  useRejectOrg,
  useRejectParticipant,
  useRejectRecord,
} from '../lib/approveActions'
import {
  Badge,
  Button,
  Card,
  CardBody,
  EmptyState,
  ErrorMessage,
  Input,
  LoadingState,
  PageHeading,
} from '../components/ui'

export const Route = createFileRoute('/approve')({
  component: ApprovePage,
})

type Tab = 'records' | 'orgs' | 'participants'

function ApprovePage() {
  const { user } = useAuth()
  const activeBranch = useActiveBranch()
  const isCentral = user?.role === 'central_admin'
  const lockedBranch = !isCentral && isBranchLocked()
  const [branchId, setBranchId] = useState(activeBranch)
  useEffect(() => {
    if (!isCentral) setBranchId(activeBranch)
  }, [activeBranch, isCentral])
  const [approvedBy, setApprovedBy] = useState(user?.full_name ?? 'Admin')
  const [tab, setTab] = useState<Tab>('records')

  // Fetch all three pending lists
  const recordsQ = useQuery({
    queryKey: ['branch-pending', branchId],
    queryFn: async () => {
      if (!branchId) return [] as Array<Record<string, unknown>>
      const { data, error } = await api.GET('/api/branch/{branch_id}/pending', {
        params: { path: { branch_id: branchId } },
      })
      if (error) throw error
      return (data ?? []) as Array<Record<string, unknown>>
    },
    enabled: Boolean(branchId),
  })

  const orgsPendingQ = useQuery({
    queryKey: ['organizations-pending', branchId],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/organizations')
      if (error) throw error
      const all = (data ?? []) as Array<Record<string, unknown>>
      const pending = all.filter((o) => o.status === 'pending')
      // Branch-admin: API already scopes; central can filter by branchId if entered
      if (isCentral && branchId) return pending.filter((o) => String(o.branch_id) === branchId)
      return pending
    },
  })

  const participantsPendingQ = useQuery({
    queryKey: ['participants-pending', branchId],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/participants', {
        params: { query: branchId ? { branch_id: branchId, limit: 1000 } : { limit: 1000 } },
      })
      if (error) throw error
      const all = (data ?? []) as Array<Record<string, unknown>>
      return all.filter((p) => p.status === 'pending')
    },
  })

  const recordsRows = recordsQ.data ?? []
  const orgRows = orgsPendingQ.data ?? []
  const participantRows = participantsPendingQ.data ?? []

  const tabs: Array<{ id: Tab; label: string; count: number }> = [
    { id: 'records', label: 'Records', count: recordsRows.length },
    { id: 'orgs', label: 'Organizations', count: orgRows.length },
    { id: 'participants', label: 'Participants', count: participantRows.length },
  ]

  return (
    <div className="grid gap-4">
      <PageHeading
        title="Approve Queue"
        subtitle={`รวม ${recordsRows.length + orgRows.length + participantRows.length} รายการรออนุมัติ`}
        right={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              recordsQ.refetch()
              orgsPendingQ.refetch()
              participantsPendingQ.refetch()
            }}
          >
            Refresh
          </Button>
        }
      />

      <Card>
        <CardBody className="flex flex-wrap items-end gap-4">
          <label className="grid gap-1">
            <span className="text-xs text-slate-500">Branch ID</span>
            <Input value={branchId} onChange={(e) => setBranchId(e.target.value)} disabled={lockedBranch} className="!w-28" />
          </label>
          <label className="grid gap-1">
            <span className="text-xs text-slate-500">Approved by (records)</span>
            <Input value={approvedBy} onChange={(e) => setApprovedBy(e.target.value)} className="!w-56" />
          </label>
        </CardBody>
      </Card>

      <div className="flex gap-1 border-b border-slate-200">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition ${
              tab === t.id
                ? 'border-blue-600 text-blue-700'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            {t.label}
            {t.count > 0 && (
              <span
                className={`ml-2 px-1.5 py-0.5 rounded-full text-xs ${
                  tab === t.id ? 'bg-blue-100 text-blue-800' : 'bg-slate-200 text-slate-700'
                }`}
              >
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {tab === 'records' && (
        <RecordsTab branchId={branchId} approvedBy={approvedBy} rows={recordsRows} query={recordsQ} />
      )}
      {tab === 'orgs' && <OrgsTab rows={orgRows} query={orgsPendingQ} />}
      {tab === 'participants' && <ParticipantsTab rows={participantRows} query={participantsPendingQ} />}
    </div>
  )
}

// ─── Records tab ──────────────────────────────────────────────────

function RecordsTab({
  branchId,
  approvedBy,
  rows,
  query,
}: {
  branchId: string
  approvedBy: string
  rows: Array<Record<string, unknown>>
  query: { isLoading: boolean; error: unknown }
}) {
  const approve = useApproveRecord()
  const reject = useRejectRecord()
  const [busy, setBusy] = useState(false)

  async function approveAll() {
    if (!confirm(`อนุมัติทั้งหมด ${rows.length} records?`)) return
    setBusy(true)
    for (const r of rows) {
      try {
        await approve.mutateAsync({ recordId: Number(r.id), approvedBy })
      } catch {}
    }
    setBusy(false)
  }

  if (!branchId) return <EmptyState>กรอก Branch ID เพื่อดูรายการรออนุมัติ</EmptyState>
  if (query.isLoading) return <LoadingState />
  if (query.error) return <ErrorMessage>{String(query.error)}</ErrorMessage>
  if (rows.length === 0) return <EmptyState>ไม่มี records รออนุมัติ</EmptyState>

  return (
    <div className="grid gap-3">
      <div className="flex justify-end">
        <Button variant="success" size="sm" onClick={approveAll} disabled={busy}>
          ✓ Approve all ({rows.length})
        </Button>
      </div>
      {rows.map((r) => {
        const id = Number(r.id)
        const flags = (r.flags as string[] | undefined) ?? []
        return (
          <Card key={id}>
            <CardBody className="flex items-start justify-between gap-4">
              <div className="grid gap-1.5 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-slate-900">#{id}</span>
                  <Badge tone="blue">{String(r.type ?? '')}</Badge>
                  <span className="text-xs text-slate-500">{String(r.date ?? '')}</span>
                </div>
                <div className="text-sm">
                  {String(r.org_name ?? r.name ?? '')}
                  <span className="text-slate-500 ml-2">
                    · {Number(r.total_minutes ?? r.minutes ?? 0).toLocaleString()} นาที
                  </span>
                </div>
                {flags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {flags.map((f) => (
                      <Badge key={f} tone="amber">
                        ⚠ {f}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <Button variant="success" onClick={() => approve.mutate({ recordId: id, approvedBy })}>
                  ✓ Approve
                </Button>
                <Button
                  variant="danger"
                  onClick={() => {
                    const reason = prompt('เหตุผลที่ปฏิเสธ?')
                    if (reason) reject.mutate({ recordId: id, reason })
                  }}
                >
                  ✗ Reject
                </Button>
              </div>
            </CardBody>
          </Card>
        )
      })}
      {(approve.error || reject.error) && <ErrorMessage>{String(approve.error ?? reject.error)}</ErrorMessage>}
    </div>
  )
}

// ─── Orgs tab ─────────────────────────────────────────────────────

function OrgsTab({
  rows,
  query,
}: {
  rows: Array<Record<string, unknown>>
  query: { isLoading: boolean; error: unknown }
}) {
  const approve = useApproveOrg()
  const reject = useRejectOrg()
  const [busy, setBusy] = useState(false)

  async function approveAll() {
    if (!confirm(`อนุมัติทั้งหมด ${rows.length} องค์กร?`)) return
    setBusy(true)
    for (const o of rows) {
      try {
        await approve.mutateAsync(String(o.id))
      } catch {}
    }
    setBusy(false)
  }

  if (query.isLoading) return <LoadingState />
  if (query.error) return <ErrorMessage>{String(query.error)}</ErrorMessage>
  if (rows.length === 0) return <EmptyState>ไม่มีองค์กรรออนุมัติ</EmptyState>

  return (
    <div className="grid gap-3">
      <div className="flex justify-end">
        <Button variant="success" size="sm" onClick={approveAll} disabled={busy}>
          ✓ Approve all ({rows.length})
        </Button>
      </div>
      {rows.map((o) => {
        const id = String(o.id)
        return (
          <Card key={id}>
            <CardBody className="flex items-start justify-between gap-4">
              <div className="grid gap-1 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">{id}</code>
                  <Badge tone="purple">{String(o.org_type ?? 'องค์กร')}</Badge>
                  <span className="text-xs text-slate-500">สาขา {String(o.branch_id ?? '')}</span>
                </div>
                <div className="font-medium">{String(o.name ?? '')}</div>
                <div className="text-xs text-slate-500">
                  {String(o.province ?? '')}
                  {o.contact_phone ? ` · ${String(o.contact_phone)}` : ''}
                  {o.contact_name ? ` · ${String(o.contact_name)}` : ''}
                </div>
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <Button variant="success" onClick={() => approve.mutate(id)}>
                  ✓ Approve
                </Button>
                <Button variant="danger" onClick={() => reject.mutate(id)}>
                  ✗ Reject
                </Button>
              </div>
            </CardBody>
          </Card>
        )
      })}
      {(approve.error || reject.error) && <ErrorMessage>{String(approve.error ?? reject.error)}</ErrorMessage>}
    </div>
  )
}

// ─── Participants tab ─────────────────────────────────────────────

function ParticipantsTab({
  rows,
  query,
}: {
  rows: Array<Record<string, unknown>>
  query: { isLoading: boolean; error: unknown }
}) {
  const approve = useApproveParticipant()
  const reject = useRejectParticipant()
  const [busy, setBusy] = useState(false)

  async function approveAll() {
    if (!confirm(`อนุมัติทั้งหมด ${rows.length} ผู้เข้าร่วม?`)) return
    setBusy(true)
    for (const p of rows) {
      try {
        await approve.mutateAsync(Number(p.id))
      } catch {}
    }
    setBusy(false)
  }

  if (query.isLoading) return <LoadingState />
  if (query.error) return <ErrorMessage>{String(query.error)}</ErrorMessage>
  if (rows.length === 0) return <EmptyState>ไม่มีผู้เข้าร่วมรออนุมัติ</EmptyState>

  return (
    <div className="grid gap-3">
      <div className="flex justify-end">
        <Button variant="success" size="sm" onClick={approveAll} disabled={busy}>
          ✓ Approve all ({rows.length})
        </Button>
      </div>
      {rows.map((p) => {
        const id = Number(p.id)
        return (
          <Card key={id}>
            <CardBody className="flex items-start justify-between gap-4">
              <div className="grid gap-1 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-slate-500 text-xs">#{id}</span>
                  <Badge tone="blue">{String(p.gender ?? '—')}</Badge>
                  <span className="text-xs text-slate-500">สาขา {String(p.branch_id ?? '')}</span>
                </div>
                <div className="font-medium">
                  {String(p.prefix ?? '')} {String(p.first_name ?? '')} {String(p.last_name ?? '')}
                </div>
                <div className="text-xs text-slate-500">
                  {String(p.province ?? '')}
                  {p.phone ? ` · ${String(p.phone)}` : ''}
                  {p.age != null ? ` · อายุ ${String(p.age)}` : ''}
                </div>
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <Button variant="success" onClick={() => approve.mutate(id)}>
                  ✓ Approve
                </Button>
                <Button variant="danger" onClick={() => reject.mutate(id)}>
                  ✗ Reject
                </Button>
              </div>
            </CardBody>
          </Card>
        )
      })}
      {(approve.error || reject.error) && <ErrorMessage>{String(approve.error ?? reject.error)}</ErrorMessage>}
    </div>
  )
}

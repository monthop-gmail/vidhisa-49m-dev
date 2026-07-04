import { createFileRoute } from '@tanstack/react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../lib/auth'
import { Modal } from '../components/Modal'
import { useSortable } from '../lib/sort'
import {
  Badge,
  Button,
  Card,
  CardBody,
  EmptyState,
  ErrorMessage,
  Field,
  Input,
  LoadingState,
  PageHeading,
  Select,
  SortableTh,
  StatusBadge,
  Table,
  Td,
  Th,
  Thead,
  Tr,
} from '../components/ui'

type SortKey = 'id' | 'branch_number' | 'branch_name' | 'status'

export const Route = createFileRoute('/enrollments')({
  component: EnrollmentsPage,
})

type Enrollment = Record<string, unknown>
type StatusFilter = '' | 'pending' | 'approved' | 'rejected'

function EnrollmentsPage() {
  const { user } = useAuth()
  const isCentral = user?.role === 'central_admin'
  const qc = useQueryClient()
  const [q, setQ] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('')
  const [editingBranch, setEditingBranch] = useState<Enrollment | null>(null)
  const [syncResult, setSyncResult] = useState<unknown>(null)
  const { sort, toggleSort, sortRows } = useSortable<Enrollment, SortKey>({
    defaultSort: { key: 'id', dir: 'desc' },
  })

  const { data, isLoading, error } = useQuery({
    queryKey: ['enrollments'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/enrollments')
      if (error) throw error
      return (data ?? []) as Enrollment[]
    },
  })

  const approveMut = useMutation({
    mutationFn: async (id: number) => {
      const { data, error } = await api.PATCH('/api/enrollments/{enrollment_id}/approve', {
        params: { path: { enrollment_id: id } },
      })
      if (error) throw error
      return data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['enrollments'] }),
  })

  const rejectMut = useMutation({
    mutationFn: async (id: number) => {
      const { data, error } = await api.PATCH('/api/enrollments/{enrollment_id}/reject', {
        params: { path: { enrollment_id: id } },
      })
      if (error) throw error
      return data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['enrollments'] }),
  })

  const syncMut = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST('/api/enrollments/sync')
      if (error) throw error
      return data
    },
    onSuccess: (data) => {
      setSyncResult(data)
      qc.invalidateQueries({ queryKey: ['enrollments'] })
    },
  })

  if (isLoading) return <LoadingState />
  if (error) return <ErrorMessage>{String(error)}</ErrorMessage>

  const all = data ?? []
  const filtered = sortRows(
    all.filter((e) => {
      if (statusFilter && e.status !== statusFilter) return false
      if (q) {
        const hay = `${e.id ?? ''} ${e.branch_number ?? ''} ${e.branch_name ?? ''} ${e.admin1_email ?? ''} ${e.admin2_email ?? ''} ${e.admin3_email ?? ''}`.toLowerCase()
        if (!hay.includes(q.toLowerCase())) return false
      }
      return true
    }),
  )

  const pendingCount = all.filter((e) => e.status === 'pending').length

  return (
    <div className="grid gap-4">
      <PageHeading
        title="Branch Enrollments"
        subtitle={
          isCentral
            ? `${all.length} ทั้งหมด · pending ${pendingCount}`
            : `${all.length} รายการของสาขาที่คุณดูแล`
        }
        right={
          isCentral ? (
            <Button onClick={() => syncMut.mutate()} disabled={syncMut.isPending}>
              {syncMut.isPending ? 'Syncing…' : 'Sync from Google Sheet'}
            </Button>
          ) : null
        }
      />

      <Card>
        <CardBody className="flex flex-wrap items-end gap-3">
          <label className="grid gap-1">
            <span className="text-xs text-slate-500">Status</span>
            <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as StatusFilter)} className="!w-36">
              <option value="">— ทุก status —</option>
              <option value="pending">pending</option>
              <option value="approved">approved</option>
              <option value="rejected">rejected</option>
            </Select>
          </label>
          <label className="grid gap-1 ml-auto">
            <span className="text-xs text-slate-500">ค้นหา</span>
            <Input
              placeholder="ชื่อสาขา / เลขสาขา / email"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="!w-80"
            />
          </label>
        </CardBody>
      </Card>

      <Card>
        <CardBody className="p-0">
          {filtered.length === 0 ? (
            <div className="p-8">
              <EmptyState>ไม่พบ enrollments</EmptyState>
            </div>
          ) : (
            <Table>
              <Thead>
                <Tr>
                  <SortableTh sortKey="id" sort={sort} onSort={toggleSort}>ID</SortableTh>
                  <SortableTh sortKey="branch_number" sort={sort} onSort={toggleSort}>เลขสาขา</SortableTh>
                  <SortableTh sortKey="branch_name" sort={sort} onSort={toggleSort}>ชื่อสาขา</SortableTh>
                  <Th>Admins</Th>
                  <SortableTh sortKey="status" sort={sort} onSort={toggleSort}>Status</SortableTh>
                  {isCentral && <Th align="right">Actions</Th>}
                </Tr>
              </Thead>
              <tbody>
                {filtered.map((e) => {
                  const id = Number(e.id)
                  const status = String(e.status ?? '')
                  const isMutating =
                    (approveMut.isPending && approveMut.variables === id) ||
                    (rejectMut.isPending && rejectMut.variables === id)
                  return (
                    <Tr key={id}>
                      <Td className="text-slate-500">#{id}</Td>
                      <Td>
                        <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">
                          {e.branch_number ? String(e.branch_number) : '—'}
                        </code>
                      </Td>
                      <Td>{String(e.branch_name ?? '')}</Td>
                      <Td>
                        <AdminsList enrollment={e} />
                      </Td>
                      <Td>
                        <StatusBadge status={status} />
                      </Td>
                      {isCentral && (
                        <Td align="right">
                          <div className="flex gap-2 justify-end">
                            <Button size="sm" variant="secondary" onClick={() => setEditingBranch(e)}>
                              แก้เลข
                            </Button>
                            {status === 'pending' && (
                              <>
                                <Button
                                  size="sm"
                                  variant="success"
                                  onClick={() => approveMut.mutate(id)}
                                  disabled={isMutating}
                                >
                                  Approve
                                </Button>
                                <Button
                                  size="sm"
                                  variant="danger"
                                  onClick={() => {
                                    if (confirm('ปฏิเสธสาขานี้?')) rejectMut.mutate(id)
                                  }}
                                  disabled={isMutating}
                                >
                                  Reject
                                </Button>
                              </>
                            )}
                            {status === 'rejected' && (
                              <Button
                                size="sm"
                                variant="success"
                                onClick={() => {
                                  if (confirm('สาขานี้ถูก reject ไปแล้ว — อนุมัติใหม่?')) approveMut.mutate(id)
                                }}
                                disabled={isMutating}
                              >
                                Approve (กลับมาอนุมัติ)
                              </Button>
                            )}
                          </div>
                        </Td>
                      )}
                    </Tr>
                  )
                })}
              </tbody>
            </Table>
          )}
        </CardBody>
      </Card>

      {(approveMut.error || rejectMut.error || syncMut.error) && (
        <ErrorMessage>{String(approveMut.error ?? rejectMut.error ?? syncMut.error)}</ErrorMessage>
      )}

      <BranchNumberModal enrollment={editingBranch} onClose={() => setEditingBranch(null)} />
      <SyncResultModal result={syncResult} onClose={() => setSyncResult(null)} />
    </div>
  )
}

// ─── Admins (3 lines) ─────────────────────────────────────────────

function AdminsList({ enrollment }: { enrollment: Enrollment }) {
  const admins = [
    { name: enrollment.admin1_name, email: enrollment.admin1_email },
    { name: enrollment.admin2_name, email: enrollment.admin2_email },
    { name: enrollment.admin3_name, email: enrollment.admin3_email },
  ].filter((a) => a.name || a.email)
  if (admins.length === 0) return <span className="text-xs text-slate-400">—</span>
  return (
    <div className="grid gap-0.5 text-xs">
      {admins.map((a, i) => (
        <div key={i}>
          <span className="text-slate-700">{String(a.name ?? '—')}</span>
          {a.email ? <span className="text-slate-400 ml-1">· {String(a.email)}</span> : null}
        </div>
      ))}
    </div>
  )
}

// ─── Edit branch number modal ─────────────────────────────────────

function BranchNumberModal({
  enrollment,
  onClose,
}: {
  enrollment: Enrollment | null
  onClose: () => void
}) {
  const qc = useQueryClient()
  const [num, setNum] = useState('')

  if (enrollment && num === '') {
    setNum(String(enrollment.branch_number ?? ''))
  }

  const updateMut = useMutation({
    mutationFn: async (branchNumber: string) => {
      const { data, error } = await api.PATCH('/api/enrollments/{enrollment_id}/update-branch', {
        params: { path: { enrollment_id: Number(enrollment?.id) } },
        body: { branch_number: branchNumber },
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['enrollments'] })
      handleClose()
    },
  })

  function handleClose() {
    setNum('')
    onClose()
  }

  return (
    <Modal
      open={enrollment !== null}
      onClose={handleClose}
      title={`แก้เลขสาขา · ${enrollment?.branch_name ?? ''}`}
      width="max-w-md"
    >
      {enrollment && (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            updateMut.mutate(num)
          }}
          className="grid gap-3"
        >
          <Field label="เลขสาขา (3 หลัก)">
            <Input
              value={num}
              onChange={(e) => setNum(e.target.value)}
              placeholder="เช่น 058"
              maxLength={3}
              autoFocus
            />
          </Field>
          <p className="text-xs text-slate-500">
            ปัจจุบัน: <code className="bg-slate-100 px-1.5 py-0.5 rounded">{enrollment.branch_number ? String(enrollment.branch_number) : 'ว่าง'}</code>
          </p>
          <div className="flex gap-3 mt-2 pt-3 border-t border-slate-100">
            <Button type="submit" disabled={updateMut.isPending}>
              {updateMut.isPending ? 'Saving…' : 'Save'}
            </Button>
            <Button type="button" variant="secondary" onClick={handleClose}>
              Cancel
            </Button>
            {updateMut.error && <ErrorMessage>{String(updateMut.error)}</ErrorMessage>}
          </div>
        </form>
      )}
    </Modal>
  )
}

// ─── Sync result modal ────────────────────────────────────────────

function SyncResultModal({ result, onClose }: { result: unknown; onClose: () => void }) {
  return (
    <Modal open={result !== null} onClose={onClose} title="Sync result" width="max-w-2xl">
      <pre className="bg-slate-50 border border-slate-200 rounded-md p-3 text-xs whitespace-pre-wrap max-h-96 overflow-y-auto">
        {result ? JSON.stringify(result, null, 2) : ''}
      </pre>
    </Modal>
  )
}

// ─── Status badge with dot ────────────────────────────────────────

// Re-export for clarity (already in ui)
export { Badge as _Badge }

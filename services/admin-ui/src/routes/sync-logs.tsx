import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getToken, useAuth } from '../lib/auth'
import { useActiveBranch } from '../lib/activeBranch'
import { Modal } from '../components/Modal'
import {
  Badge,
  Card,
  CardBody,
  EmptyState,
  ErrorMessage,
  Field,
  LoadingState,
  PageHeading,
  Select,
  Table,
  Td,
  Th,
  Thead,
  Tr,
} from '../components/ui'

export const Route = createFileRoute('/sync-logs')({
  component: SyncLogsPage,
})

type SyncLog = {
  id: number
  branch_id: string | null
  sync_type: string
  started_at: string | null
  finished_at: string | null
  status: 'ok' | 'error' | 'partial'
  created: number
  updated: number
  participants_created: number
  error_count: number
  message: string | null
  triggered_by: string
}

type SyncErrorItem = string | { branch_id?: string; errors?: string[] }
type SyncLogDetail = SyncLog & { errors: SyncErrorItem[] }

async function fetchLogs(params: { branch_id?: string; status?: string; limit?: number }) {
  const qs = new URLSearchParams()
  if (params.branch_id) qs.set('branch_id', params.branch_id)
  if (params.status) qs.set('status', params.status)
  qs.set('limit', String(params.limit ?? 100))
  const r = await fetch(`/api/ggs/sync-logs?${qs.toString()}`, {
    headers: { Authorization: `Bearer ${getToken() ?? ''}` },
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return (await r.json()) as SyncLog[]
}

async function fetchDetail(id: number) {
  const r = await fetch(`/api/ggs/sync-logs/${id}`, {
    headers: { Authorization: `Bearer ${getToken() ?? ''}` },
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return (await r.json()) as SyncLogDetail
}

function statusBadge(s: string) {
  if (s === 'ok') return <Badge tone="green">ok</Badge>
  if (s === 'error') return <Badge tone="red">error</Badge>
  return <Badge tone="amber">partial</Badge>
}

function fmt(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('th-TH', { hour12: false })
}

function SyncLogsPage() {
  const { user } = useAuth()
  const activeBranch = useActiveBranch()
  const [statusFilter, setStatusFilter] = useState('')
  const [detailId, setDetailId] = useState<number | null>(null)

  // ถ้า central + active branch → filter, ว่าง → ทุกสาขา
  // Branch admin → activeBranch = สาขาตัวเอง (locked)
  const branchFilter = activeBranch

  const { data: logs, isLoading, error } = useQuery({
    queryKey: ['sync-logs', branchFilter, statusFilter],
    queryFn: () => fetchLogs({ branch_id: branchFilter || undefined, status: statusFilter || undefined }),
    refetchInterval: 60_000,
  })

  const { data: detail } = useQuery({
    queryKey: ['sync-log-detail', detailId],
    queryFn: () => fetchDetail(detailId!),
    enabled: detailId !== null,
  })

  return (
    <div className="max-w-6xl mx-auto p-4 space-y-4">
      <PageHeading
        title="Sync Logs"
        subtitle={
          <span>
            ประวัติการซิงค์ Google Sheet · {branchFilter ? `focus ${branchFilter}` : 'ทุกสาขา'} · auto-refresh 60 วิ
            <span className="ml-2 text-blue-600">← คลิกแถวเพื่อดูรายละเอียด</span>
          </span>
        }
      />

      <Card>
        <CardBody>
          <div className="flex flex-wrap gap-3 items-end">
            <Field label="สถานะ">
              <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                <option value="">ทั้งหมด</option>
                <option value="ok">ok</option>
                <option value="partial">partial (มี errors บางแถว)</option>
                <option value="error">error (fail ทั้งหมด)</option>
              </Select>
            </Field>
            {user?.role === 'central_admin' && (
              <div className="text-xs text-slate-500 self-end pb-1">
                ⓘ เปลี่ยนสาขาที่ focus ได้ที่ switcher มุมขวาบน
              </div>
            )}
          </div>
        </CardBody>
      </Card>

      {isLoading && <LoadingState />}
      {error && <ErrorMessage>{(error as Error).message}</ErrorMessage>}
      {logs && logs.length === 0 && <EmptyState>ยังไม่มี log — รอ auto-sync รอบต่อไป</EmptyState>}
      {logs && logs.length > 0 && (
        <Card>
          <div className="overflow-x-auto">
            <Table>
              <Thead>
                <Tr>
                  <Th>เริ่ม</Th>
                  <Th>สาขา</Th>
                  <Th>ประเภท</Th>
                  <Th>สถานะ</Th>
                  <Th align="right">created</Th>
                  <Th align="right">updated</Th>
                  <Th align="right">errors</Th>
                  <Th>trigger</Th>
                  <Th align="right"></Th>
                </Tr>
              </Thead>
              <tbody>
                {logs.map((log) => (
                  <Tr
                    key={log.id}
                    className="cursor-pointer hover:bg-blue-50 transition"
                    onClick={() => setDetailId(log.id)}
                  >
                    <Td>{fmt(log.started_at)}</Td>
                    <Td>{log.branch_id ?? <span className="text-slate-500">— (batch)</span>}</Td>
                    <Td>{log.sync_type}</Td>
                    <Td>{statusBadge(log.status)}</Td>
                    <Td align="right">{log.created}</Td>
                    <Td align="right">{log.updated}</Td>
                    <Td align="right">
                      {log.error_count > 0 ? (
                        <span className="text-red-700 font-medium">{log.error_count}</span>
                      ) : (
                        '0'
                      )}
                    </Td>
                    <Td>{log.triggered_by}</Td>
                    <Td align="right">
                      <span className="text-blue-600 text-sm">ดูรายละเอียด →</span>
                    </Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          </div>
        </Card>
      )}

      <Modal open={detailId !== null} onClose={() => setDetailId(null)} title="Sync Log Detail">
        {!detail ? (
          <LoadingState />
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div><span className="text-slate-500">Log ID:</span> {detail.id}</div>
              <div><span className="text-slate-500">Status:</span> {statusBadge(detail.status)}</div>
              <div><span className="text-slate-500">Branch:</span> {detail.branch_id ?? '— (batch)'}</div>
              <div><span className="text-slate-500">Type:</span> {detail.sync_type}</div>
              <div><span className="text-slate-500">Started:</span> {fmt(detail.started_at)}</div>
              <div><span className="text-slate-500">Finished:</span> {fmt(detail.finished_at)}</div>
              <div><span className="text-slate-500">Created:</span> {detail.created}</div>
              <div><span className="text-slate-500">Updated:</span> {detail.updated}</div>
              <div><span className="text-slate-500">Trigger:</span> {detail.triggered_by}</div>
              <div><span className="text-slate-500">Errors:</span> {detail.error_count}</div>
            </div>
            {detail.message && (
              <div className="rounded bg-slate-100 p-2 text-sm">
                <div className="text-slate-500 text-xs mb-1">Summary</div>
                {detail.message}
              </div>
            )}
            {detail.errors && detail.errors.length > 0 && (
              <div>
                <div className="text-slate-500 text-xs mb-1">Errors (max 100)</div>
                <div className="max-h-96 overflow-y-auto rounded border border-slate-200">
                  <ul className="divide-y divide-slate-200 text-sm">
                    {detail.errors.map((e, i) => (
                      <li key={i} className="p-2">
                        {typeof e === 'string' ? (
                          e
                        ) : (
                          <>
                            <span className="font-medium">{e.branch_id}:</span>{' '}
                            {(e.errors ?? []).join(' | ')}
                          </>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

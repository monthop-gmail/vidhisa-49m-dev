import { createFileRoute } from '@tanstack/react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../lib/auth'
import { useActiveBranch } from '../lib/activeBranch'
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
  SortableTh,
  Table,
  Td,
  Th,
  Thead,
  Tr,
} from '../components/ui'

type GgsSortKey = 'branch_id' | 'branch_name' | 'group_id' | 'configured'

export const Route = createFileRoute('/ggs')({
  component: GgsPage,
})

const URL_TYPES = [
  { key: 'ggs_url_org', label: 'Organizations', short: 'org' },
  { key: 'ggs_url_participant', label: 'Participants', short: 'participant' },
  { key: 'ggs_url_record_bulk', label: 'Records (bulk)', short: 'record_bulk' },
  { key: 'ggs_url_record_ind', label: 'Records (individual)', short: 'record_ind' },
] as const

type Source = {
  branch_id: string
  branch_name: string
  group_id: string | null
  ggs_url_org: string | null
  ggs_url_participant: string | null
  ggs_url_record_bulk: string | null
  ggs_url_record_ind: string | null
}

function GgsPage() {
  const { user } = useAuth()
  const isCentral = user?.role === 'central_admin'
  const [q, setQ] = useState('')
  const [editing, setEditing] = useState<Source | null>(null)
  const [syncResult, setSyncResult] = useState<unknown>(null)
  const { sort, toggleSort, sortRows } = useSortable<Source, GgsSortKey>({
    defaultSort: { key: 'branch_id', dir: 'asc' },
    getValue: (r, k) => {
      if (k === 'configured') {
        return (r.ggs_url_org ? 1 : 0) + (r.ggs_url_participant ? 1 : 0) + (r.ggs_url_record_bulk ? 1 : 0) + (r.ggs_url_record_ind ? 1 : 0)
      }
      return r[k]
    },
  })

  const { data, isLoading, error } = useQuery({
    queryKey: ['ggs-sources'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/ggs/sources')
      if (error) throw error
      return (data ?? []) as Source[]
    },
  })

  const activeBranch = useActiveBranch()
  const allRows = data ?? []
  // central admin: ทุกสาขา (หรือ active filter ถ้าเลือก)
  // branch admin หลายสาขา: filter ตาม branch_ids (หรือ active แค่สาขาเดียว)
  const userBranchIds = user?.branch_ids && user.branch_ids.length > 0 ? user.branch_ids : (user?.branch_id ? [user.branch_id] : [])
  const rowsForUser = isCentral
    ? (activeBranch ? allRows.filter((r) => r.branch_id === activeBranch) : allRows)
    : (activeBranch ? allRows.filter((r) => r.branch_id === activeBranch) : allRows.filter((r) => userBranchIds.includes(r.branch_id as string)))
  const filtered = sortRows(
    q
      ? rowsForUser.filter((r) =>
          `${r.branch_id} ${r.branch_name} ${r.group_id ?? ''}`.toLowerCase().includes(q.toLowerCase()),
        )
      : rowsForUser,
  )

  // ─── per-branch sync ──────────────────────────────────────────
  const syncOneMut = useMutation({
    mutationFn: async (branchId: string) => {
      const { data, error } = await api.POST('/api/ggs/sync-branch', {
        body: { branch_id: branchId, auto_approve: false },
      })
      if (error) throw error
      return data
    },
    onSuccess: (data) => setSyncResult(data),
  })

  // ─── central-only mutations ───────────────────────────────────
  const syncAllMut = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST('/api/ggs/sync-all', {
        body: { auto_approve: true },
      })
      if (error) throw error
      return data
    },
    onSuccess: (data) => setSyncResult(data),
  })

  const syncOrgEnrollMut = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST('/api/ggs/sync-org-enrollments')
      if (error) throw error
      return data
    },
    onSuccess: (data) => setSyncResult(data),
  })

  if (isLoading) return <LoadingState />
  if (error) return <ErrorMessage>{String(error)}</ErrorMessage>

  return (
    <div className="grid gap-4">
      <PageHeading
        title="Google Sheets Sources"
        subtitle={isCentral ? `จัดการ URLs และ sync ทุกสาขา (${allRows.length})` : `URLs ของสาขา ${user?.branch_id}`}
        right={
          isCentral && (
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => syncOrgEnrollMut.mutate()}
                disabled={syncOrgEnrollMut.isPending}
              >
                {syncOrgEnrollMut.isPending ? 'Syncing…' : 'Sync external orgs'}
              </Button>
              <Button
                onClick={() => {
                  if (confirm('Sync ทุกสาขาที่ตั้ง URL ไว้? (auto-approve จะถูกใช้)')) syncAllMut.mutate()
                }}
                disabled={syncAllMut.isPending}
              >
                {syncAllMut.isPending ? 'Syncing all…' : 'Sync all branches'}
              </Button>
            </div>
          )
        }
      />

      {isCentral && (
        <Card>
          <CardBody className="flex items-end gap-3">
            <Input placeholder="ค้นหา branch_id / ชื่อ / group" value={q} onChange={(e) => setQ(e.target.value)} className="!w-80" />
            <span className="text-sm text-slate-500 ml-auto">
              {countConfigured(filtered)} / {filtered.length} สาขามี URL อย่างน้อย 1 ตัว
            </span>
          </CardBody>
        </Card>
      )}

      <Card>
        <CardBody className="p-0">
          {filtered.length === 0 ? (
            <div className="p-8">
              <EmptyState>ไม่พบสาขา</EmptyState>
            </div>
          ) : (
            <Table>
              <Thead>
                <Tr>
                  <SortableTh sortKey="branch_id" sort={sort} onSort={toggleSort}>Branch</SortableTh>
                  <SortableTh sortKey="group_id" sort={sort} onSort={toggleSort}>Group</SortableTh>
                  <SortableTh sortKey="configured" sort={sort} onSort={toggleSort} align="center">URLs ตั้งแล้ว</SortableTh>
                  <Th align="center">Org</Th>
                  <Th align="center">Participant</Th>
                  <Th align="center">Bulk</Th>
                  <Th align="center">Individual</Th>
                  <Th align="right">Actions</Th>
                </Tr>
              </Thead>
              <tbody>
                {filtered.slice(0, 400).map((r) => {
                  const count =
                    (r.ggs_url_org ? 1 : 0) +
                    (r.ggs_url_participant ? 1 : 0) +
                    (r.ggs_url_record_bulk ? 1 : 0) +
                    (r.ggs_url_record_ind ? 1 : 0)
                  return (
                  <Tr key={r.branch_id}>
                    <Td>
                      <div className="flex items-center gap-2">
                        <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">{r.branch_id}</code>
                        <span className="text-slate-700">{r.branch_name}</span>
                      </div>
                    </Td>
                    <Td className="text-slate-500 text-xs">{r.group_id ?? '—'}</Td>
                    <Td align="center" className="text-xs text-slate-500">{count}/4</Td>
                    <UrlCell url={r.ggs_url_org} />
                    <UrlCell url={r.ggs_url_participant} />
                    <UrlCell url={r.ggs_url_record_bulk} />
                    <UrlCell url={r.ggs_url_record_ind} />
                    <Td align="right">
                      <div className="flex gap-2 justify-end">
                        <Button size="sm" variant="secondary" onClick={() => setEditing(r)}>
                          Edit URLs
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => syncOneMut.mutate(r.branch_id)}
                          disabled={
                            syncOneMut.isPending ||
                            (!r.ggs_url_org && !r.ggs_url_participant && !r.ggs_url_record_bulk && !r.ggs_url_record_ind)
                          }
                        >
                          {syncOneMut.isPending && syncOneMut.variables === r.branch_id ? 'Syncing…' : 'Sync'}
                        </Button>
                      </div>
                    </Td>
                  </Tr>
                  )
                })}
              </tbody>
            </Table>
          )}
        </CardBody>
      </Card>

      {filtered.length > 400 && (
        <div className="text-xs text-slate-500">แสดง 400 รายการแรกจาก {filtered.length}</div>
      )}

      {(syncOneMut.error || syncAllMut.error || syncOrgEnrollMut.error) && (
        <ErrorMessage>{String(syncOneMut.error ?? syncAllMut.error ?? syncOrgEnrollMut.error)}</ErrorMessage>
      )}

      <EditUrlsModal source={editing} onClose={() => setEditing(null)} />
      <SyncResultModal result={syncResult} onClose={() => setSyncResult(null)} />
    </div>
  )
}

// ─── URL status cell ──────────────────────────────────────────────

function UrlCell({ url }: { url: string | null }) {
  return (
    <Td align="center">
      {url ? (
        <a href={url} target="_blank" rel="noreferrer" title={url}>
          <Badge tone="green">✓</Badge>
        </a>
      ) : (
        <Badge tone="gray">—</Badge>
      )}
    </Td>
  )
}

// ─── Edit URLs modal ──────────────────────────────────────────────

function EditUrlsModal({ source, onClose }: { source: Source | null; onClose: () => void }) {
  const qc = useQueryClient()
  const [form, setForm] = useState<Record<string, string>>({})

  // Reset form when source changes
  if (source && Object.keys(form).length === 0) {
    setForm({
      ggs_url_org: source.ggs_url_org ?? '',
      ggs_url_participant: source.ggs_url_participant ?? '',
      ggs_url_record_bulk: source.ggs_url_record_bulk ?? '',
      ggs_url_record_ind: source.ggs_url_record_ind ?? '',
    })
  }

  const saveMut = useMutation({
    mutationFn: async (body: Record<string, string>) => {
      const { data, error } = await api.PATCH('/api/ggs/set-url', { body })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ggs-sources'] })
      handleClose()
    },
  })

  function handleClose() {
    setForm({})
    onClose()
  }

  return (
    <Modal open={source !== null} onClose={handleClose} title={`Edit URLs · ${source?.branch_id ?? ''} ${source?.branch_name ?? ''}`}>
      {source && (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            saveMut.mutate({ branch_id: source.branch_id, ...form })
          }}
          className="grid gap-3"
        >
          {URL_TYPES.map((t) => (
            <Field key={t.key} label={t.label}>
              <Input
                value={form[t.key] ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, [t.key]: e.target.value }))}
                placeholder="https://docs.google.com/spreadsheets/d/..."
              />
            </Field>
          ))}

          <div className="flex flex-wrap items-center gap-3 mt-2 pt-3 border-t border-slate-100">
            <Button type="submit" disabled={saveMut.isPending}>
              {saveMut.isPending ? 'Saving…' : 'Save URLs'}
            </Button>
            <Button type="button" variant="secondary" onClick={handleClose}>
              Cancel
            </Button>
            {saveMut.error && <ErrorMessage>{String(saveMut.error)}</ErrorMessage>}
          </div>

          <p className="text-xs text-slate-500 pt-2">
            Tip: ใส่ URL ทั้งสี่แบบจาก Google Sheets ก็พอ — ระบบจะ normalize เป็น gviz JSON format ให้อัตโนมัติ
          </p>
        </form>
      )}
    </Modal>
  )
}

// ─── Sync result modal ────────────────────────────────────────────

function SyncResultModal({ result, onClose }: { result: unknown; onClose: () => void }) {
  // สรุปตัวเลขจาก result ให้อ่านง่าย (นับ error_count รวมทุกประเภท sync)
  const summary = extractSyncSummary(result)
  return (
    <Modal open={result !== null} onClose={onClose} title="Sync Result">
      {summary && (
        <div className="mb-3 flex flex-wrap gap-2 text-xs">
          <span className="bg-emerald-100 text-emerald-800 px-2 py-1 rounded-full">
            created {summary.created.toLocaleString()}
          </span>
          <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
            updated {summary.updated.toLocaleString()}
          </span>
          {summary.participants_created > 0 && (
            <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded-full">
              participants +{summary.participants_created.toLocaleString()}
            </span>
          )}
          {summary.error_count > 0 && (
            <span className="bg-amber-100 text-amber-800 px-2 py-1 rounded-full font-medium">
              ⚠ {summary.error_count.toLocaleString()} errors
              {summary.error_count > (summary.errors_shown ?? 10) && (
                <span className="ml-1 text-amber-700 opacity-80">
                  (แสดง {summary.errors_shown ?? 10} ตัวอย่าง — ดูทั้งหมดที่ /sync-logs)
                </span>
              )}
            </span>
          )}
        </div>
      )}
      <pre className="bg-slate-50 border border-slate-200 rounded-md p-3 text-xs whitespace-pre-wrap max-h-96 overflow-y-auto">
        {result ? JSON.stringify(result, null, 2) : ''}
      </pre>
    </Modal>
  )
}

type SyncSummary = {
  created: number
  updated: number
  participants_created: number
  error_count: number
  errors_shown?: number
}

function extractSyncSummary(result: unknown): SyncSummary | null {
  if (!result || typeof result !== 'object') return null
  const r = result as Record<string, unknown>
  // sync-branch response: { branch_id, record_ind: {...}, org: {...}, ... }
  const sub = r.record_ind ?? r.participant ?? r  // นับ record_ind ก่อน, ไม่มีก็ participant, ไม่มีก็ top-level (sync-all)
  const s = sub as Record<string, unknown>
  return {
    created: Number(s.created ?? 0),
    updated: Number(s.updated ?? 0),
    participants_created: Number(s.participants_created ?? 0),
    error_count: Number(s.error_count ?? (Array.isArray(s.errors) ? s.errors.length : 0)),
    errors_shown: Array.isArray(s.errors) ? s.errors.length : undefined,
  }
}

function countConfigured(rows: Source[]): number {
  return rows.filter(
    (r) => r.ggs_url_org || r.ggs_url_participant || r.ggs_url_record_bulk || r.ggs_url_record_ind,
  ).length
}

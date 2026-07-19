import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { api } from '../api/client'
import { Modal } from './Modal'
import { Badge, EmptyState, ErrorMessage, LoadingState, StatusBadge, Table, Td, Th, Thead, Tr } from './ui'

// ─── Org detail ───────────────────────────────────────────────────

export function OrgDetailModal({ orgId, onClose }: { orgId: string | null; onClose: () => void }) {
  const open = orgId !== null
  const { data: org, isLoading, error } = useQuery({
    queryKey: ['organization-detail', orgId],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/organizations/{org_id}', {
        params: { path: { org_id: orgId! } },
      })
      if (error) throw error
      return data as Record<string, unknown>
    },
    enabled: open,
  })

  const { data: records } = useQuery({
    queryKey: ['organization-records', orgId],
    queryFn: async () => {
      // ใช้ backend filter (org_id) แทน fetch สาขาทั้งหมด → กัน records ขาดกรณีสาขาใหญ่
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data, error } = await api.GET('/api/records', {
        params: { query: { org_id: orgId, limit: 5000 } as any },
      })
      if (error) throw error
      return (data ?? []) as Array<Record<string, unknown>>
    },
    enabled: open && Boolean(orgId),
  })

  const recList = records ?? []
  const approved = recList.filter((r) => r.status === 'approved')
  const totalMin = approved.reduce((s, r) => s + Number(r.minutes ?? 0), 0)

  return (
    <Modal open={open} onClose={onClose} title={`Organization · ${orgId ?? ''}`} width="max-w-3xl">
      {isLoading && <LoadingState />}
      {error && <ErrorMessage>{String(error)}</ErrorMessage>}
      {org && (
        <div className="grid gap-4">
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            <Field label="ชื่อ" value={String(org.name ?? '')} />
            <Field label="ประเภท" value={String(org.org_type ?? '')} />
            <Field label="สาขา" value={String(org.branch_id ?? '')} />
            <Field label="จังหวัด" value={String(org.province ?? '')} />
            <Field label="ผู้ติดต่อ" value={String(org.contact_name ?? '')} />
            <Field label="เบอร์โทร" value={String(org.contact_phone ?? '')} />
            <Field label="อีเมล" value={String(org.email ?? '')} />
            <Field
              label="Status"
              value={org.status ? <StatusBadge status={String(org.status)} /> : '—'}
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <Stat label="Records ทั้งหมด" value={recList.length.toLocaleString()} />
            <Stat label="Approved" value={approved.length.toLocaleString()} tone="green" />
            <Stat label="นาทีรวม" value={totalMin.toLocaleString()} />
          </div>

          <div>
            <div className="text-sm font-semibold text-slate-700 mb-2">Records ล่าสุด</div>
            {recList.length === 0 ? (
              <EmptyState>ยังไม่มี records</EmptyState>
            ) : (
              <Table>
                <Thead>
                  <Tr>
                    <Th>วันที่</Th>
                    <Th align="right">นาที</Th>
                    <Th>Status</Th>
                  </Tr>
                </Thead>
                <tbody>
                  {recList
                    .slice()
                    .sort((a, b) => String(b.date).localeCompare(String(a.date)))
                    .slice(0, 10)
                    .map((r) => (
                      <Tr key={Number(r.id)}>
                        <Td>{String(r.date ?? '')}</Td>
                        <Td align="right">{Number(r.minutes ?? 0).toLocaleString()}</Td>
                        <Td>
                          <StatusBadge status={String(r.status ?? '')} />
                        </Td>
                      </Tr>
                    ))}
                </tbody>
              </Table>
            )}
          </div>

          <div className="flex justify-end pt-2 border-t border-slate-100">
            <Link
              to="/organizations/$orgId"
              params={{ orgId: String(orgId) }}
              className="text-sm text-blue-600 hover:underline"
              onClick={onClose}
            >
              เปิดหน้า edit →
            </Link>
          </div>
        </div>
      )}
    </Modal>
  )
}

// ─── Participant detail ───────────────────────────────────────────

export function ParticipantDetailModal({ participantId, onClose }: { participantId: number | null; onClose: () => void }) {
  const open = participantId !== null
  const { data: p, isLoading, error } = useQuery({
    queryKey: ['participant-detail', participantId],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/participants/{participant_id}', {
        params: { path: { participant_id: participantId! } },
      })
      if (error) throw error
      return data as Record<string, unknown>
    },
    enabled: open,
  })

  const { data: records } = useQuery({
    queryKey: ['participant-records', participantId, p?.branch_id],
    queryFn: async () => {
      // ใช้ backend filter ตรง (participant_id) แทน fetch สาขาทั้งหมดแล้ว filter client-side
      // (สาขาใหญ่มี records > 2000 → filter client-side จะขาด)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data, error } = await api.GET('/api/records', {
        params: { query: { participant_id: participantId, limit: 5000 } as any },
      })
      if (error) throw error
      return (data ?? []) as Array<Record<string, unknown>>
    },
    enabled: open && Boolean(participantId),
  })

  const recList = records ?? []
  const approved = recList.filter((r) => r.status === 'approved')
  const totalMin = approved.reduce((s, r) => s + Number(r.minutes ?? 0), 0)
  const distinctDays = new Set(recList.map((r) => String(r.date ?? ''))).size

  return (
    <Modal open={open} onClose={onClose} title={`Participant · #${participantId ?? ''}`} width="max-w-3xl">
      {isLoading && <LoadingState />}
      {error && <ErrorMessage>{String(error)}</ErrorMessage>}
      {p && (
        <div className="grid gap-4">
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            <Field
              label="ชื่อ"
              value={`${p.prefix ?? ''} ${p.first_name ?? ''} ${p.last_name ?? ''}`.trim()}
            />
            <Field label="เพศ" value={p.gender ? <Badge tone="blue">{String(p.gender)}</Badge> : '—'} />
            <Field label="อายุ" value={p.age != null ? String(p.age) : '—'} />
            <Field label="สาขา" value={String(p.branch_id ?? '')} />
            <Field label="จังหวัด" value={String(p.province ?? '')} />
            <Field label="เบอร์โทร" value={String(p.phone ?? '')} />
            <Field label="Status" value={p.status ? <StatusBadge status={String(p.status)} /> : '—'} />
            <Field label="ลงทะเบียน" value={String(p.enrolled_date ?? '')} />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <Stat label="Records" value={recList.length.toLocaleString()} />
            <Stat label="Approved" value={approved.length.toLocaleString()} tone="green" />
            <Stat label="นาทีรวม" value={totalMin.toLocaleString()} sub={`${distinctDays} วันที่ปฏิบัติ`} />
          </div>

          <div>
            <div className="text-sm font-semibold text-slate-700 mb-2">Records ล่าสุด</div>
            {recList.length === 0 ? (
              <EmptyState>ยังไม่มี records</EmptyState>
            ) : (
              <Table>
                <Thead>
                  <Tr>
                    <Th>วันที่</Th>
                    <Th align="right">นาที</Th>
                    <Th>Status</Th>
                  </Tr>
                </Thead>
                <tbody>
                  {recList
                    .slice()
                    .sort((a, b) => String(b.date).localeCompare(String(a.date)))
                    .slice(0, 10)
                    .map((r) => (
                      <Tr key={Number(r.id)}>
                        <Td>{String(r.date ?? '')}</Td>
                        <Td align="right">{Number(r.minutes ?? 0).toLocaleString()}</Td>
                        <Td>
                          <StatusBadge status={String(r.status ?? '')} />
                        </Td>
                      </Tr>
                    ))}
                </tbody>
              </Table>
            )}
          </div>

          <div className="flex justify-end pt-2 border-t border-slate-100">
            <Link
              to="/participants/$participantId"
              params={{ participantId: String(participantId) }}
              className="text-sm text-blue-600 hover:underline"
              onClick={onClose}
            >
              เปิดหน้า edit →
            </Link>
          </div>
        </div>
      )}
    </Modal>
  )
}

// ─── shared bits ──────────────────────────────────────────────────

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-sm text-slate-900">{value || <span className="text-slate-400">—</span>}</div>
    </div>
  )
}

function Stat({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: 'green' }) {
  return (
    <div className={`border rounded-md p-3 ${tone === 'green' ? 'bg-green-50 border-green-200' : 'bg-slate-50 border-slate-200'}`}>
      <div className="text-xs text-slate-500">{label}</div>
      <div className={`text-2xl font-bold ${tone === 'green' ? 'text-green-700' : 'text-slate-900'} tabular-nums`}>{value}</div>
      {sub && <div className="text-xs text-slate-500 mt-0.5">{sub}</div>}
    </div>
  )
}

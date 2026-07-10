import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../lib/auth'
import { useActiveBranch, isBranchLocked } from '../lib/activeBranch'
import { usePagination, splitPage } from '../lib/pagination'
import { useSortable } from '../lib/sort'
import { Pagination } from '../components/Pagination'
import { ParticipantDetailModal } from '../components/DetailDrawer'
import {
  Button,
  Card,
  CardBody,
  EmptyState,
  ErrorMessage,
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

export const Route = createFileRoute('/participants/')({
  component: ParticipantsListPage,
})

const PAGE_SIZE = 50

type SortKey = 'id' | 'member_code' | 'fullName' | 'gender' | 'age' | 'branch_id' | 'province' | 'phone' | 'status' | 'total_minutes'
type StatusFilter = '' | 'pending' | 'approved' | 'rejected'

function ParticipantsListPage() {
  const { user } = useAuth()
  const activeBranch = useActiveBranch()
  const isCentral = user?.role === 'central_admin'
  const lockedBranch = !isCentral && isBranchLocked()
  const [q, setQ] = useState('')
  const [branchId, setBranchId] = useState(activeBranch)
  const [status, setStatus] = useState<StatusFilter>('approved') // default filter = approved
  useEffect(() => {
    if (!isCentral) setBranchId(activeBranch)
  }, [activeBranch, isCentral])
  const [detailId, setDetailId] = useState<number | null>(null)

  const filtersKey = JSON.stringify({ branchId, status })
  const { page, pageSize, offset, probeLimit, setPage } = usePagination(PAGE_SIZE, filtersKey)
  const { sort, toggleSort, sortRows } = useSortable<Record<string, unknown>, SortKey>({
    getValue: (r, k) => {
      if (k === 'fullName') return `${r.first_name ?? ''} ${r.last_name ?? ''}`
      if (k === 'member_code') return r.member_code ?? ''
      if (k === 'total_minutes') return Number(r.total_minutes ?? 0)
      return r[k]
    },
  })

  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ['participants', branchId, status, page],
    queryFn: async () => {
      const query: Record<string, string | number> = { limit: probeLimit, offset }
      if (branchId) query.branch_id = branchId
      if (status) query.status = status
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data, error } = await api.GET('/api/participants', { params: { query: query as any } })
      if (error) throw error
      return data
    },
    placeholderData: (prev) => prev,
  })

  if (isLoading) return <LoadingState />
  if (error) return <ErrorMessage>{String(error)}</ErrorMessage>

  const allRows = (Array.isArray(data) ? data : []) as Array<Record<string, unknown>>
  const { visible: pagedRows, hasNext } = splitPage(allRows, pageSize)
  const searched = q
    ? pagedRows.filter((r) =>
        `${r.id ?? ''} ${r.member_code ?? ''} ${r.first_name ?? ''} ${r.last_name ?? ''} ${r.phone ?? ''} ${r.province ?? ''}`
          .toLowerCase()
          .includes(q.toLowerCase()),
      )
    : pagedRows
  const rows = sortRows(searched)

  return (
    <div className="grid gap-4">
      <PageHeading
        title="Participants"
        subtitle={isFetching ? 'กำลังโหลด…' : 'รายการผู้เข้าร่วม'}
        right={
          <Link to="/participants/new">
            <Button>+ New</Button>
          </Link>
        }
      />

      <Card>
        <CardBody className="flex flex-wrap items-end gap-3">
          <label className="grid gap-1">
            <span className="text-xs text-slate-500">Branch ID</span>
            <Input
              value={branchId}
              onChange={(e) => setBranchId(e.target.value)}
              disabled={lockedBranch}
              className="!w-28"
              placeholder="เช่น B020"
            />
          </label>
          <label className="grid gap-1">
            <span className="text-xs text-slate-500">Status</span>
            <Select value={status} onChange={(e) => setStatus(e.target.value as StatusFilter)} className="!w-36">
              <option value="">— ทุก status —</option>
              <option value="pending">pending</option>
              <option value="approved">approved</option>
              <option value="rejected">rejected</option>
            </Select>
          </label>
          <label className="grid gap-1 ml-auto">
            <span className="text-xs text-slate-500">ค้นหา</span>
            <Input
              placeholder="id / code / ชื่อ / เบอร์"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="!w-64"
            />
          </label>
        </CardBody>
      </Card>

      <Card>
        <CardBody className="p-0">
          {rows.length === 0 ? (
            <div className="p-8">
              <EmptyState>{page > 0 ? 'หน้านี้ว่าง — กดย้อนกลับ' : 'ไม่พบผู้เข้าร่วม'}</EmptyState>
            </div>
          ) : (
            <Table>
              <Thead>
                <Tr>
                  <SortableTh sortKey="id" sort={sort} onSort={toggleSort}>ID</SortableTh>
                  <SortableTh sortKey="member_code" sort={sort} onSort={toggleSort}>Code</SortableTh>
                  <SortableTh sortKey="fullName" sort={sort} onSort={toggleSort}>ชื่อ-นามสกุล</SortableTh>
                  <SortableTh sortKey="gender" sort={sort} onSort={toggleSort}>เพศ</SortableTh>
                  <SortableTh sortKey="age" sort={sort} onSort={toggleSort} align="right">อายุ</SortableTh>
                  <SortableTh sortKey="branch_id" sort={sort} onSort={toggleSort}>สาขา</SortableTh>
                  <SortableTh sortKey="province" sort={sort} onSort={toggleSort}>จังหวัด</SortableTh>
                  <SortableTh sortKey="phone" sort={sort} onSort={toggleSort}>เบอร์โทร</SortableTh>
                  <SortableTh sortKey="total_minutes" sort={sort} onSort={toggleSort} align="right">นาที</SortableTh>
                  <SortableTh sortKey="status" sort={sort} onSort={toggleSort}>Status</SortableTh>
                  <Th></Th>
                </Tr>
              </Thead>
              <tbody>
                {rows.map((r) => (
                  <Tr key={String(r.id)}>
                    <Td>
                      <button onClick={() => setDetailId(Number(r.id))} className="text-blue-600 hover:underline">
                        #{String(r.id ?? '')}
                      </button>
                    </Td>
                    <Td>
                      {r.member_code ? (
                        <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded font-mono">
                          {String(r.member_code)}
                        </code>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </Td>
                    <Td>
                      <button onClick={() => setDetailId(Number(r.id))} className="text-left hover:underline">
                        {String(r.prefix ?? '')} {String(r.first_name ?? '')} {String(r.last_name ?? '')}
                      </button>
                    </Td>
                    <Td className="text-slate-600">{String(r.gender ?? '')}</Td>
                    <Td align="right">{r.age != null ? String(r.age) : ''}</Td>
                    <Td>
                      <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">{String(r.branch_id ?? '')}</code>
                    </Td>
                    <Td className="text-slate-600">{String(r.province ?? '')}</Td>
                    <Td className="text-slate-600">{String(r.phone ?? '')}</Td>
                    <Td align="right" className="font-medium tabular-nums">
                      {Number(r.total_minutes ?? 0).toLocaleString()}
                    </Td>
                    <Td>{r.status ? <StatusBadge status={String(r.status)} /> : null}</Td>
                    <Td>
                      <Link
                        to="/participants/$participantId"
                        params={{ participantId: String(r.id) }}
                        className="text-blue-600 hover:underline text-sm"
                      >
                        Edit →
                      </Link>
                    </Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          )}
        </CardBody>
      </Card>

      <Pagination page={page} hasNext={hasNext} onChange={setPage} visibleCount={pagedRows.length} pageSize={pageSize} />

      <ParticipantDetailModal participantId={detailId} onClose={() => setDetailId(null)} />
    </div>
  )
}

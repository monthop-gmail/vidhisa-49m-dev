import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../lib/auth'
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

type SortKey = 'id' | 'fullName' | 'gender' | 'age' | 'branch_id' | 'province' | 'phone' | 'status'

function ParticipantsListPage() {
  const { user } = useAuth()
  const isCentral = user?.role === 'central_admin'
  const lockedBranch = !isCentral && Boolean(user?.branch_id)
  const [q, setQ] = useState('')
  const [branchId, setBranchId] = useState(user?.branch_id ?? '')
  const [detailId, setDetailId] = useState<number | null>(null)

  const filtersKey = JSON.stringify({ branchId })
  const { page, pageSize, offset, probeLimit, setPage } = usePagination(PAGE_SIZE, filtersKey)
  const { sort, toggleSort, sortRows } = useSortable<Record<string, unknown>, SortKey>({
    getValue: (r, k) => {
      if (k === 'fullName') return `${r.first_name ?? ''} ${r.last_name ?? ''}`
      return r[k]
    },
  })

  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ['participants', branchId, page],
    queryFn: async () => {
      const query: Record<string, string | number> = { limit: probeLimit, offset }
      if (branchId) query.branch_id = branchId
      const { data, error } = await api.GET('/api/participants', { params: { query } })
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
        `${r.id ?? ''} ${r.first_name ?? ''} ${r.last_name ?? ''} ${r.phone ?? ''} ${r.province ?? ''}`
          .toLowerCase()
          .includes(q.toLowerCase()),
      )
    : pagedRows
  const rows = sortRows(searched)

  return (
    <div className="grid gap-4">
      <PageHeading
        title="Participants"
        subtitle={isFetching ? 'กำลังโหลด…' : `แสดงรายการตาม filter`}
        right={
          <div className="flex items-center gap-2">
            <Input
              placeholder="Branch ID"
              value={branchId}
              onChange={(e) => setBranchId(e.target.value)}
              disabled={lockedBranch}
              className="!w-32"
            />
            <Input placeholder="ค้นหาในหน้านี้" value={q} onChange={(e) => setQ(e.target.value)} className="!w-56" />
            <Link to="/participants/new">
              <Button>+ New</Button>
            </Link>
          </div>
        }
      />

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
                  <SortableTh sortKey="fullName" sort={sort} onSort={toggleSort}>ชื่อ-นามสกุล</SortableTh>
                  <SortableTh sortKey="gender" sort={sort} onSort={toggleSort}>เพศ</SortableTh>
                  <SortableTh sortKey="age" sort={sort} onSort={toggleSort} align="right">อายุ</SortableTh>
                  <SortableTh sortKey="branch_id" sort={sort} onSort={toggleSort}>สาขา</SortableTh>
                  <SortableTh sortKey="province" sort={sort} onSort={toggleSort}>จังหวัด</SortableTh>
                  <SortableTh sortKey="phone" sort={sort} onSort={toggleSort}>เบอร์โทร</SortableTh>
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

import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../lib/auth'
import { useActiveBranch, isBranchLocked } from '../lib/activeBranch'
import { usePagination, splitPage } from '../lib/pagination'
import { useSortable } from '../lib/sort'
import { Pagination } from '../components/Pagination'
import { useApproveRecord, useRejectRecord } from '../lib/approveActions'
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

type SortKey = 'id' | 'type' | 'branch_id' | 'name' | 'minutes' | 'date' | 'status'

export const Route = createFileRoute('/records/')({
  component: RecordsPage,
})

type RecordType = '' | 'bulk' | 'individual'
type RecordStatus = '' | 'pending' | 'approved' | 'rejected'

const PAGE_SIZE = 50

function RecordsPage() {
  const { user } = useAuth()
  const activeBranch = useActiveBranch()
  const isCentral = user?.role === 'central_admin'
  const lockedBranch = !isCentral && isBranchLocked()
  const [branchId, setBranchId] = useState(activeBranch)

  // sync with navbar branch switcher
  useEffect(() => {
    if (!isCentral) setBranchId(activeBranch)
  }, [activeBranch, isCentral])
  const [type, setType] = useState<RecordType>('')
  const [status, setStatus] = useState<RecordStatus>('')
  const [approvedBy, setApprovedBy] = useState(user?.full_name ?? 'Admin')

  const filtersKey = JSON.stringify({ branchId, type, status })
  const { page, pageSize, offset, probeLimit, setPage } = usePagination(PAGE_SIZE, filtersKey)
  const { sort, toggleSort, sortRows } = useSortable<Record<string, unknown>, SortKey>({
    getValue: (r, k) => {
      if (k === 'minutes') return Number(r.minutes ?? 0)
      if (k === 'name') return r.name ?? r.org_id ?? ''
      return r[k]
    },
  })

  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ['records', branchId, type, status, page],
    queryFn: async () => {
      const query: Record<string, string | number> = { limit: probeLimit, offset }
      if (branchId) query.branch_id = branchId
      if (type) query.record_type = type
      if (status) query.status = status
      const { data, error } = await api.GET('/api/records', { params: { query } })
      if (error) throw error
      return data
    },
    placeholderData: (prev) => prev,
  })

  const approve = useApproveRecord()
  const reject = useRejectRecord()

  if (isLoading) return <LoadingState />
  if (error) return <ErrorMessage>{String(error)}</ErrorMessage>

  const allRows = (Array.isArray(data) ? data : []) as Array<Record<string, unknown>>
  const { visible: pagedRows, hasNext } = splitPage(allRows, pageSize)
  const rows = sortRows(pagedRows)

  return (
    <div className="grid gap-4">
      <PageHeading
        title="Records"
        subtitle={isFetching ? 'กำลังโหลด…' : 'รายการบันทึก'}
        right={
          <Link to="/records/new">
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
            />
          </label>
          <label className="grid gap-1">
            <span className="text-xs text-slate-500">Type</span>
            <Select value={type} onChange={(e) => setType(e.target.value as RecordType)} className="!w-36">
              <option value="">— ทุก type —</option>
              <option value="bulk">bulk</option>
              <option value="individual">individual</option>
            </Select>
          </label>
          <label className="grid gap-1">
            <span className="text-xs text-slate-500">Status</span>
            <Select value={status} onChange={(e) => setStatus(e.target.value as RecordStatus)} className="!w-36">
              <option value="">— ทุก status —</option>
              <option value="pending">pending</option>
              <option value="approved">approved</option>
              <option value="rejected">rejected</option>
            </Select>
          </label>
          <label className="grid gap-1 ml-auto">
            <span className="text-xs text-slate-500">Approved by</span>
            <Input value={approvedBy} onChange={(e) => setApprovedBy(e.target.value)} className="!w-48" />
          </label>
        </CardBody>
      </Card>

      <Card>
        <CardBody className="p-0">
          {rows.length === 0 ? (
            <div className="p-8">
              <EmptyState>{page > 0 ? 'หน้านี้ว่าง — กดย้อนกลับ' : 'ไม่พบ records'}</EmptyState>
            </div>
          ) : (
            <Table>
              <Thead>
                <Tr>
                  <SortableTh sortKey="id" sort={sort} onSort={toggleSort}>ID</SortableTh>
                  <SortableTh sortKey="type" sort={sort} onSort={toggleSort}>Type</SortableTh>
                  <SortableTh sortKey="branch_id" sort={sort} onSort={toggleSort}>Branch</SortableTh>
                  <SortableTh sortKey="name" sort={sort} onSort={toggleSort}>ชื่อ/Org</SortableTh>
                  <SortableTh sortKey="minutes" sort={sort} onSort={toggleSort} align="right">นาที</SortableTh>
                  <SortableTh sortKey="date" sort={sort} onSort={toggleSort}>วันที่</SortableTh>
                  <SortableTh sortKey="status" sort={sort} onSort={toggleSort}>Status</SortableTh>
                  <Th>Actions</Th>
                </Tr>
              </Thead>
              <tbody>
                {rows.map((r) => {
                  const id = Number(r.id)
                  const st = String(r.status ?? '')
                  return (
                    <Tr key={id}>
                      <Td className="text-slate-500">#{id}</Td>
                      <Td className="text-slate-600">{String(r.type ?? '')}</Td>
                      <Td>
                        <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">{String(r.branch_id ?? '')}</code>
                      </Td>
                      <Td>{String(r.name ?? r.org_id ?? '')}</Td>
                      <Td align="right">{Number(r.minutes ?? 0).toLocaleString()}</Td>
                      <Td className="text-slate-600">{String(r.date ?? '')}</Td>
                      <Td>
                        <StatusBadge status={st} />
                      </Td>
                      <Td>
                        {st === 'pending' ? (
                          <div className="flex gap-1.5">
                            <Button
                              size="sm"
                              variant="success"
                              onClick={() => approve.mutate({ recordId: id, approvedBy })}
                              disabled={approve.isPending}
                            >
                              Approve
                            </Button>
                            <Button
                              size="sm"
                              variant="danger"
                              onClick={() => {
                                const reason = prompt('เหตุผลที่ปฏิเสธ?')
                                if (reason) reject.mutate({ recordId: id, reason })
                              }}
                              disabled={reject.isPending}
                            >
                              Reject
                            </Button>
                          </div>
                        ) : (
                          <span className="text-xs text-slate-400">—</span>
                        )}
                      </Td>
                    </Tr>
                  )
                })}
              </tbody>
            </Table>
          )}
        </CardBody>
      </Card>

      <Pagination page={page} hasNext={hasNext} onChange={setPage} visibleCount={pagedRows.length} pageSize={pageSize} />

      {(approve.error || reject.error) && (
        <ErrorMessage>{String(approve.error ?? reject.error)}</ErrorMessage>
      )}
    </div>
  )
}

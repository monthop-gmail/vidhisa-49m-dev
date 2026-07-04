import { Link, Outlet, createRootRoute, redirect, useNavigate } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/router-devtools'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { useQuery } from '@tanstack/react-query'
import { clearSession, getToken, useAuth } from '../lib/auth'
import { useActiveBranch, setActiveBranch } from '../lib/activeBranch'
import { api } from '../api/client'
import { Badge, Button, Select } from '../components/ui'

export const Route = createRootRoute({
  beforeLoad: ({ location }) => {
    if (location.pathname === '/login') return
    if (!getToken()) {
      throw redirect({ to: '/login' })
    }
  },
  component: RootLayout,
})

const NAV_LINK_BASE = 'px-3 py-1.5 text-sm rounded-md text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition'
const NAV_LINK_ACTIVE = 'bg-blue-50 text-blue-700 hover:bg-blue-50 hover:text-blue-700 font-semibold'

function RootLayout() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const isCentral = user?.role === 'central_admin'

  function logout() {
    clearSession()
    navigate({ to: '/login' })
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto flex items-center gap-6 px-6 py-3 flex-wrap">
          <Link to="/" className="font-bold text-slate-900 text-lg">
            Vidhisa <span className="text-blue-600">Admin</span>
          </Link>
          <nav className="flex items-center gap-1">
            <Link to="/" className={NAV_LINK_BASE} activeOptions={{ exact: true }} activeProps={{ className: `${NAV_LINK_BASE} ${NAV_LINK_ACTIVE}` }}>
              Dashboard
            </Link>
            <Link to="/branches" className={NAV_LINK_BASE} activeProps={{ className: `${NAV_LINK_BASE} ${NAV_LINK_ACTIVE}` }}>
              Branches
            </Link>
            {isCentral && (
              <Link to="/enrollments" className={NAV_LINK_BASE} activeProps={{ className: `${NAV_LINK_BASE} ${NAV_LINK_ACTIVE}` }}>
                Enrollments
              </Link>
            )}
            {isCentral && (
              <Link to="/users" className={NAV_LINK_BASE} activeProps={{ className: `${NAV_LINK_BASE} ${NAV_LINK_ACTIVE}` }}>
                Users
              </Link>
            )}
            <Link to="/organizations" className={NAV_LINK_BASE} activeProps={{ className: `${NAV_LINK_BASE} ${NAV_LINK_ACTIVE}` }}>
              Organizations
            </Link>
            <Link to="/participants" className={NAV_LINK_BASE} activeProps={{ className: `${NAV_LINK_BASE} ${NAV_LINK_ACTIVE}` }}>
              Participants
            </Link>
            <Link to="/records" className={NAV_LINK_BASE} activeProps={{ className: `${NAV_LINK_BASE} ${NAV_LINK_ACTIVE}` }}>
              Records
            </Link>
            <Link to="/approve" className={NAV_LINK_BASE} activeProps={{ className: `${NAV_LINK_BASE} ${NAV_LINK_ACTIVE}` }}>
              Approve
            </Link>
            <Link to="/ggs" className={NAV_LINK_BASE} activeProps={{ className: `${NAV_LINK_BASE} ${NAV_LINK_ACTIVE}` }}>
              Google Sheets
            </Link>
            <Link to="/sync-logs" className={NAV_LINK_BASE} activeProps={{ className: `${NAV_LINK_BASE} ${NAV_LINK_ACTIVE}` }}>
              Sync Logs
            </Link>
          </nav>
          {user && (
            <div className="ml-auto flex items-center gap-3 text-sm">
              <BranchSwitcher />
              <RoleBadge role={user.role} branchId={user.branch_id} />
              <span className="text-slate-700 hidden sm:inline">{user.full_name}</span>
              <Button variant="secondary" size="sm" onClick={logout}>
                Logout
              </Button>
            </div>
          )}
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-6 py-8">
        <Outlet />
      </main>
      <TanStackRouterDevtools position="bottom-right" />
      <ReactQueryDevtools buttonPosition="bottom-left" />
    </div>
  )
}

function RoleBadge({ role, branchId }: { role: string; branchId: string | null }) {
  if (role === 'central_admin') return <Badge tone="blue">CENTRAL</Badge>
  return <Badge tone="amber">BRANCH · {branchId ?? '?'}</Badge>
}

function BranchSwitcher() {
  const { user } = useAuth()
  const active = useActiveBranch()
  const isCentral = user?.role === 'central_admin'

  // Central: fetch all 325 branches for typeahead
  const { data: allBranches } = useQuery({
    queryKey: ['branches-switcher'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/branches')
      if (error) throw error
      return (Array.isArray(data) ? data : []) as Array<{ id: string; name: string; province?: string | null }>
    },
    enabled: Boolean(isCentral),
    staleTime: 5 * 60 * 1000,
  })

  if (!user) return null
  const ids = user.branch_ids && user.branch_ids.length > 0 ? user.branch_ids : (user.branch_id ? [user.branch_id] : [])

  // Central admin: typeahead input + datalist (325 branches)
  if (isCentral) {
    return (
      <>
        <input
          list="__branch_switcher_list"
          value={active}
          onChange={(e) => {
            const v = e.target.value.trim().toUpperCase()
            // Accept only if empty (=ทุกสาขา) หรือ match branch ที่มีจริง
            if (v === '' || allBranches?.some((b) => b.id === v)) {
              setActiveBranch(v)
            } else {
              setActiveBranch(v)  // เก็บค่าที่พิมพ์ไว้ก่อน — user จะเลือกจาก dropdown
            }
          }}
          placeholder="— ทุกสาขา —"
          className="rounded-md border border-slate-300 px-2 py-1 text-xs w-44 focus:outline-none focus:ring-2 focus:ring-blue-500"
          title="พิมพ์ code หรือชื่อสาขาเพื่อโฟกัส (ว่าง = ทุกสาขา)"
        />
        <datalist id="__branch_switcher_list">
          {(allBranches ?? []).map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}{b.province ? ` — ${b.province}` : ''}
            </option>
          ))}
        </datalist>
      </>
    )
  }

  // Branch admin: dropdown ถ้ามีหลายสาขา
  if (ids.length < 2) return null
  return (
    <Select
      value={active}
      onChange={(e) => setActiveBranch(e.target.value)}
      className="!w-40 !py-1 !text-xs"
      title="เลือกสาขาที่จะโฟกัส"
    >
      {ids.map((b) => (
        <option key={b} value={b}>{b}</option>
      ))}
    </Select>
  )
}

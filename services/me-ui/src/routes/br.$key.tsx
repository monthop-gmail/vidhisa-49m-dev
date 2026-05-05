import { createFileRoute, Navigate } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { parseBranchKey, getRememberedParticipant } from '../lib/branchKey'

export const Route = createFileRoute('/br/$key')({
  component: BranchLanding,
})

function BranchLanding() {
  const { key } = Route.useParams()
  const parsed = parseBranchKey(key)

  const { data: info, isLoading, isError } = useQuery({
    queryKey: ['branch-view-info', parsed?.branchId, parsed?.secret],
    queryFn: async () => {
      if (!parsed) throw new Error('invalid')
      const res = await fetch(`/api/branch-view/${parsed.branchId}/${parsed.secret}/info`)
      if (!res.ok) throw new Error(String(res.status))
      return (await res.json()) as { branch_id: string; branch_name: string; province: string }
    },
    enabled: Boolean(parsed),
    retry: false,
  })

  if (!parsed || isError) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-white rounded-2xl shadow p-8 text-center">
          <div className="text-4xl mb-3">🔒</div>
          <h1 className="text-xl font-semibold text-slate-900 mb-2">Link ไม่ถูกต้อง</h1>
          <p className="text-slate-600">กรุณาตรวจสอบ link ที่สาขาส่งให้อีกครั้ง</p>
        </div>
      </div>
    )
  }

  if (isLoading || !info) {
    return <div className="min-h-screen flex items-center justify-center text-slate-500">กำลังตรวจสอบ link…</div>
  }

  const remembered = getRememberedParticipant(parsed.branchId)
  if (remembered) {
    return <Navigate to="/br/$key/me/$participantId" params={{ key, participantId: String(remembered) }} replace />
  }
  return <Navigate to="/br/$key/search" params={{ key }} replace />
}

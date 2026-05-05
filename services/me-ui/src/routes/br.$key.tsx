import { createFileRoute, Navigate } from '@tanstack/react-router'
import { decodeBranchKey, getRememberedParticipant } from '../lib/branchKey'

export const Route = createFileRoute('/br/$key')({
  component: BranchLanding,
})

function BranchLanding() {
  const { key } = Route.useParams()
  const branchId = decodeBranchKey(key)

  if (!branchId) {
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

  const remembered = getRememberedParticipant(branchId)

  if (remembered) {
    return <Navigate to="/br/$key/me/$participantId" params={{ key, participantId: String(remembered) }} replace />
  }
  return <Navigate to="/br/$key/search" params={{ key }} replace />
}

import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useQueries } from '@tanstack/react-query'
import { api } from '../api/client'
import { decodeBranchKey, forgetParticipant } from '../lib/branchKey'

export const Route = createFileRoute('/br/$key/me/$participantId')({
  component: MyDataPage,
})

function MyDataPage() {
  const { key, participantId } = Route.useParams()
  const navigate = useNavigate()
  const branchId = decodeBranchKey(key)
  const idNum = Number(participantId)

  const queries = useQueries({
    queries: [
      {
        queryKey: ['participant', idNum],
        queryFn: async () => {
          const { data, error } = await api.GET('/api/participants/{participant_id}', {
            params: { path: { participant_id: idNum } },
          })
          if (error) throw error
          return data as Record<string, unknown>
        },
      },
      {
        queryKey: ['records-for', branchId, idNum],
        queryFn: async () => {
          const { data, error } = await api.GET('/api/records', {
            params: { query: { branch_id: branchId!, limit: 5000 } },
          })
          if (error) throw error
          return ((data ?? []) as Array<Record<string, unknown>>).filter((r) => r.participant_id === idNum)
        },
        enabled: Boolean(branchId),
      },
      {
        queryKey: ['branch-detail', branchId],
        queryFn: async () => {
          const { data, error } = await api.GET('/api/branches/{branch_id}', {
            params: { path: { branch_id: branchId! } },
          })
          if (error) throw error
          return data as Record<string, unknown>
        },
        enabled: Boolean(branchId),
      },
    ],
  })

  const [participantQ, recordsQ, branchQ] = queries
  const p = participantQ.data
  const records = (recordsQ.data ?? []) as Array<Record<string, unknown>>
  const branch = branchQ.data as Record<string, unknown> | undefined

  if (!branchId) return null

  function notMe() {
    forgetParticipant(branchId!)
    navigate({ to: '/br/$key/search', params: { key } })
  }

  if (queries.some((q) => q.isLoading)) {
    return <div className="min-h-screen flex items-center justify-center text-slate-500">กำลังโหลด…</div>
  }

  if (!p || p.branch_id !== branchId) {
    return (
      <div className="min-h-screen p-6 flex items-center justify-center">
        <div className="max-w-md w-full bg-white rounded-2xl shadow p-8 text-center">
          <h1 className="text-xl font-semibold mb-2">ไม่พบข้อมูล</h1>
          <button onClick={notMe} className="mt-4 px-5 py-2 bg-blue-600 text-white rounded-lg">
            กลับไปค้นหา
          </button>
        </div>
      </div>
    )
  }

  const approved = records.filter((r) => r.status === 'approved')
  const totalMin = approved.reduce((s, r) => s + Number(r.minutes ?? 0), 0)
  const distinctDays = new Set(approved.map((r) => String(r.date ?? ''))).size
  const sessions = approved.length

  // Daily breakdown — last 14 days
  const byDate = new Map<string, number>()
  for (const r of approved) {
    const d = String(r.date ?? '')
    if (!d) continue
    byDate.set(d, (byDate.get(d) ?? 0) + Number(r.minutes ?? 0))
  }
  const days = Array.from(byDate.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .slice(-14)

  const recent = records
    .slice()
    .sort((a, b) => String(b.date).localeCompare(String(a.date)))
    .slice(0, 10)

  // Mockup: stub Form URL until backend adds branches.record_form_url column
  // Real flow: read from branch.record_form_url
  const recordFormUrl = (branch?.record_form_url as string | null | undefined) ?? null

  const phoneMasked = maskPhone(String(p.phone ?? ''))

  return (
    <div className="min-h-screen p-4 sm:p-6 max-w-md mx-auto pb-20">
      <header className="text-center mb-6">
        <div className="text-sm text-slate-500">สาขา {branchId}</div>
        <h1 className="text-2xl font-bold text-slate-900 mt-1">
          {String(p.prefix ?? '')} {String(p.first_name ?? '')} {String(p.last_name ?? '')}
        </h1>
        {p.member_code ? <div className="text-xs text-slate-500 mt-0.5">รหัส {String(p.member_code)}</div> : null}
      </header>

      <section className="bg-gradient-to-br from-blue-600 to-blue-700 text-white rounded-2xl p-6 mb-4 text-center shadow">
        <div className="text-blue-100 text-sm">นาทีสะสมของฉัน</div>
        <div className="text-5xl font-bold mt-1 tabular-nums">{totalMin.toLocaleString()}</div>
        <div className="text-blue-100 text-sm mt-1">นาที</div>
      </section>

      <section className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200 text-center">
          <div className="text-xs text-slate-500">วันที่ปฏิบัติ</div>
          <div className="text-2xl font-bold text-slate-900 tabular-nums">{distinctDays}</div>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200 text-center">
          <div className="text-xs text-slate-500">จำนวนครั้ง</div>
          <div className="text-2xl font-bold text-slate-900 tabular-nums">{sessions}</div>
        </div>
      </section>

      {days.length > 0 && (
        <section className="bg-white rounded-xl p-4 shadow-sm border border-slate-200 mb-4">
          <div className="text-sm font-semibold text-slate-700 mb-3">ยอด {days.length} วันล่าสุด</div>
          <DailyBars data={days} />
        </section>
      )}

      {recordFormUrl && (
        <a
          href={recordFormUrl}
          target="_blank"
          rel="noreferrer"
          className="block bg-green-600 hover:bg-green-700 active:bg-green-800 text-white rounded-xl p-4 mb-4 text-center font-semibold transition shadow"
        >
          📝 บันทึกการปฏิบัติ
          <div className="text-xs text-green-100 font-normal mt-1">(เปิดฟอร์มของสาขา)</div>
        </a>
      )}

      <section className="bg-white rounded-xl shadow-sm border border-slate-200 mb-4 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-100">
          <div className="text-sm font-semibold text-slate-700">ข้อมูลของฉัน</div>
        </div>
        <dl className="divide-y divide-slate-100 text-sm">
          <ProfileRow label="เพศ" value={renderGender(p.gender)} />
          <ProfileRow label="อายุ" value={p.age != null ? `${p.age} ปี` : null} />
          <ProfileRow label="จังหวัด" value={p.province as string | null} />
          <ProfileRow label="อำเภอ" value={p.district as string | null} />
          <ProfileRow label="ตำบล" value={p.sub_district as string | null} />
          <ProfileRow label="เบอร์โทร" value={phoneMasked} />
          <ProfileRow label="Line ID" value={p.line_id as string | null} />
          <ProfileRow label="วันลงทะเบียน" value={p.enrolled_date as string | null} />
        </dl>
        <div className="px-4 py-2 text-xs text-slate-400 border-t border-slate-100 text-center">
          ⓘ ข้อมูลแก้ไขที่สาขา · ไม่สามารถแก้ในหน้านี้
        </div>
      </section>

      <section className="bg-white rounded-xl shadow-sm border border-slate-200 mb-4 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-100">
          <div className="text-sm font-semibold text-slate-700">รายการล่าสุด</div>
        </div>
        {recent.length === 0 ? (
          <div className="p-6 text-center text-slate-500 text-sm">ยังไม่มีบันทึก</div>
        ) : (
          <div>
            {recent.map((r) => {
              const status = String(r.status ?? '')
              const tone =
                status === 'approved'
                  ? 'bg-green-100 text-green-700'
                  : status === 'rejected'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-amber-100 text-amber-700'
              return (
                <div key={Number(r.id)} className="px-4 py-3 border-b border-slate-100 last:border-0 flex items-center justify-between">
                  <div>
                    <div className="text-sm text-slate-900">{String(r.date ?? '')}</div>
                    <div className="text-xs mt-0.5">
                      <span className={`px-2 py-0.5 rounded-full ${tone}`}>{status}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-semibold tabular-nums">{Number(r.minutes ?? 0)}</div>
                    <div className="text-xs text-slate-500">นาที</div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>

      <div className="text-center">
        <button onClick={notMe} className="text-sm text-slate-400 underline">
          ไม่ใช่คุณ? กลับไปค้นหา
        </button>
      </div>
    </div>
  )
}

function ProfileRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="px-4 py-2.5 flex justify-between items-center">
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-slate-900 text-right">{value || <span className="text-slate-400">—</span>}</dd>
    </div>
  )
}

function maskPhone(phone: string): string {
  if (!phone) return ''
  // Keep first 3 + last 4, mask middle as 'xxx'
  const digits = phone.replace(/[^0-9]/g, '')
  if (digits.length < 7) return phone
  return `${digits.slice(0, 3)}-xxx-${digits.slice(-4)}`
}

function renderGender(g: unknown): string | null {
  if (g === 'male') return 'ชาย'
  if (g === 'female') return 'หญิง'
  if (g === 'unspecified') return 'ไม่ระบุ'
  return null
}

function DailyBars({ data }: { data: Array<[string, number]> }) {
  const max = Math.max(1, ...data.map(([, v]) => v))
  return (
    <div className="flex items-end gap-1 h-24">
      {data.map(([date, v]) => {
        const h = `${(v / max) * 100}%`
        return (
          <div key={date} className="flex-1 flex flex-col items-center gap-1">
            <div className="w-full flex items-end justify-center" style={{ height: '100%' }}>
              <div className="w-full bg-blue-500 rounded-t" style={{ height: h }} title={`${date}: ${v} min`} />
            </div>
            <div className="text-[9px] text-slate-400 truncate w-full text-center">{date.slice(8)}</div>
          </div>
        )
      })}
    </div>
  )
}

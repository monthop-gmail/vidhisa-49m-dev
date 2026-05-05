import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { parseBranchKey, forgetParticipant } from '../lib/branchKey'

export const Route = createFileRoute('/br/$key/me/$participantId')({
  component: MyDataPage,
})

type MeResponse = {
  id: number
  prefix: string | null
  first_name: string
  last_name: string
  member_code: string | null
  branch_id: string
  branch_name: string
  profile: {
    gender: string | null
    age: number | null
    sub_district: string | null
    district: string | null
    province: string | null
    phone_masked: string | null
    line_id: string | null
    enrolled_date: string | null
    status: string
  }
  branch_links: { record_form_url: string | null }
  stats: { total_minutes: number; total_records: number; approved_records: number; distinct_days: number }
  daily_minutes: Array<{ date: string; minutes: number }>
  recent_records: Array<{ id: number; date: string; minutes: number; status: string }>
}

function MyDataPage() {
  const { key, participantId } = Route.useParams()
  const navigate = useNavigate()
  const parsed = parseBranchKey(key)
  const idNum = Number(participantId)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['branch-view-me', parsed?.branchId, parsed?.secret, idNum],
    queryFn: async () => {
      if (!parsed) throw new Error('invalid')
      const res = await fetch(`/api/branch-view/${parsed.branchId}/${parsed.secret}/me/${idNum}`)
      if (!res.ok) throw new Error(String(res.status))
      return (await res.json()) as MeResponse
    },
    enabled: Boolean(parsed),
    retry: false,
  })

  if (!parsed) return null

  function notMe() {
    if (parsed) forgetParticipant(parsed.branchId)
    navigate({ to: '/br/$key/search', params: { key } })
  }

  if (isLoading) {
    return <div className="min-h-screen flex items-center justify-center text-slate-500">กำลังโหลด…</div>
  }

  if (isError || !data) {
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

  const days = data.daily_minutes.slice(-14)
  const recordFormUrl = data.branch_links.record_form_url

  return (
    <div className="min-h-screen p-4 sm:p-6 max-w-md mx-auto pb-20">
      <header className="text-center mb-6">
        <div className="text-sm text-slate-500">สาขา {data.branch_id}</div>
        <h1 className="text-2xl font-bold text-slate-900 mt-1">
          {data.prefix ?? ''} {data.first_name} {data.last_name}
        </h1>
        {data.member_code ? <div className="text-xs text-slate-500 mt-0.5">รหัส {data.member_code}</div> : null}
      </header>

      <section className="bg-gradient-to-br from-blue-600 to-blue-700 text-white rounded-2xl p-6 mb-4 text-center shadow">
        <div className="text-blue-100 text-sm">นาทีสะสมของฉัน</div>
        <div className="text-5xl font-bold mt-1 tabular-nums">{data.stats.total_minutes.toLocaleString()}</div>
        <div className="text-blue-100 text-sm mt-1">นาที</div>
      </section>

      <section className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200 text-center">
          <div className="text-xs text-slate-500">วันที่ปฏิบัติ</div>
          <div className="text-2xl font-bold text-slate-900 tabular-nums">{data.stats.distinct_days}</div>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200 text-center">
          <div className="text-xs text-slate-500">จำนวนครั้ง</div>
          <div className="text-2xl font-bold text-slate-900 tabular-nums">{data.stats.approved_records}</div>
        </div>
      </section>

      {days.length > 0 && (
        <section className="bg-white rounded-xl p-4 shadow-sm border border-slate-200 mb-4">
          <div className="text-sm font-semibold text-slate-700 mb-3">ยอด {days.length} วันล่าสุด</div>
          <DailyBars data={days.map((d) => [d.date, d.minutes])} />
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
          <ProfileRow label="เพศ" value={renderGender(data.profile.gender)} />
          <ProfileRow label="อายุ" value={data.profile.age != null ? `${data.profile.age} ปี` : null} />
          <ProfileRow label="จังหวัด" value={data.profile.province} />
          <ProfileRow label="อำเภอ" value={data.profile.district} />
          <ProfileRow label="ตำบล" value={data.profile.sub_district} />
          <ProfileRow label="เบอร์โทร" value={data.profile.phone_masked} />
          <ProfileRow label="Line ID" value={data.profile.line_id} />
          <ProfileRow label="วันลงทะเบียน" value={data.profile.enrolled_date} />
        </dl>
        <div className="px-4 py-2 text-xs text-slate-400 border-t border-slate-100 text-center">
          ⓘ ข้อมูลแก้ไขที่สาขา · ไม่สามารถแก้ในหน้านี้
        </div>
      </section>

      <section className="bg-white rounded-xl shadow-sm border border-slate-200 mb-4 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-100">
          <div className="text-sm font-semibold text-slate-700">รายการล่าสุด</div>
        </div>
        {data.recent_records.length === 0 ? (
          <div className="p-6 text-center text-slate-500 text-sm">ยังไม่มีบันทึก</div>
        ) : (
          <div>
            {data.recent_records.map((r) => {
              const tone =
                r.status === 'approved'
                  ? 'bg-green-100 text-green-700'
                  : r.status === 'rejected'
                    ? 'bg-red-100 text-red-700'
                    : 'bg-amber-100 text-amber-700'
              return (
                <div key={r.id} className="px-4 py-3 border-b border-slate-100 last:border-0 flex items-center justify-between">
                  <div>
                    <div className="text-sm text-slate-900">{r.date}</div>
                    <div className="text-xs mt-0.5">
                      <span className={`px-2 py-0.5 rounded-full ${tone}`}>{r.status}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-semibold tabular-nums">{r.minutes}</div>
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

function renderGender(g: string | null): string | null {
  if (g === 'male' || g === 'ชาย') return 'ชาย'
  if (g === 'female' || g === 'หญิง') return 'หญิง'
  if (g === 'unspecified' || g === 'ไม่ระบุ') return 'ไม่ระบุ'
  return g
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

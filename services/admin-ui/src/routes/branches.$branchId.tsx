import { createFileRoute, redirect, useNavigate } from '@tanstack/react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { getAuth } from '../lib/auth'
import { Button, Card, CardBody, ErrorMessage, Field, Input, LoadingState, PageHeading } from '../components/ui'

function MemberLinkCard({ link }: { link: string }) {
  const [copied, setCopied] = useState(false)
  async function copy() {
    try {
      await navigator.clipboard.writeText(link)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // fallback: select-all
      const i = document.getElementById('member-link-input') as HTMLInputElement | null
      i?.select()
      document.execCommand('copy')
      setCopied(true)
    }
  }
  return (
    <Card>
      <CardBody className="grid gap-3">
        <div>
          <div className="text-sm font-semibold text-slate-900">Member view link</div>
          <div className="text-xs text-slate-500 mt-0.5">
            ส่ง link นี้ใน Line ของสาขา ผู้เข้าร่วมจะค้นชื่อตัวเองเพื่อดูยอดของตน
          </div>
        </div>
        <div className="flex gap-2">
          <input
            id="member-link-input"
            value={link}
            readOnly
            onFocus={(e) => e.currentTarget.select()}
            className="flex-1 px-3 py-2 text-sm bg-slate-50 border border-slate-300 rounded-md font-mono"
          />
          <Button onClick={copy} variant={copied ? 'success' : 'primary'}>
            {copied ? '✓ Copied' : 'Copy'}
          </Button>
        </div>
        <div className="text-xs text-slate-500">
          ⓘ ผู้ที่มี link นี้เข้าค้นชื่อตัวเองได้ (เห็นยอดของผู้เข้าร่วมในสาขาเดียวกันได้)
        </div>
      </CardBody>
    </Card>
  )
}

export const Route = createFileRoute('/branches/$branchId')({
  beforeLoad: () => {
    const { user } = getAuth()
    if (user && user.role !== 'central_admin') {
      throw redirect({ to: '/' })
    }
  },
  component: BranchEditPage,
})

type Form = {
  name: string
  group_id: string
  province: string
  province_code: string
  latitude: string // keep as string for input control
  longitude: string
  admin_name: string
  contact: string
  record_form_url: string
}

function BranchEditPage() {
  const { branchId } = Route.useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['branch', branchId],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/branches/{branch_id}', {
        params: { path: { branch_id: branchId } },
      })
      if (error) throw error
      return data as Record<string, unknown>
    },
  })

  const { data: viewLink } = useQuery({
    queryKey: ['branch-view-link', branchId],
    queryFn: async () => {
      const token = getAuth().token
      const res = await fetch(`/api/branches/${branchId}/view-link`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error(String(res.status))
      return (await res.json()) as { branch_id: string; view_secret: string; view_url_path: string }
    },
  })

  const [form, setForm] = useState<Form>({
    name: '',
    group_id: '',
    province: '',
    province_code: '',
    latitude: '',
    longitude: '',
    admin_name: '',
    contact: '',
    record_form_url: '',
  })
  const [savedAt, setSavedAt] = useState<string | null>(null)

  useEffect(() => {
    if (!data) return
    setForm({
      name: String(data.name ?? ''),
      group_id: String(data.group_id ?? ''),
      province: String(data.province ?? ''),
      province_code: String(data.province_code ?? ''),
      latitude: data.latitude != null ? String(data.latitude) : '',
      longitude: data.longitude != null ? String(data.longitude) : '',
      admin_name: String(data.admin_name ?? ''),
      contact: String(data.contact ?? ''),
      record_form_url: String(data.record_form_url ?? ''),
    })
  }, [data])

  const saveMut = useMutation({
    mutationFn: async (f: Form) => {
      const body: Record<string, unknown> = {
        name: f.name,
        group_id: f.group_id || null,
        province: f.province || null,
        province_code: f.province_code || null,
        latitude: f.latitude === '' ? null : Number(f.latitude),
        longitude: f.longitude === '' ? null : Number(f.longitude),
        admin_name: f.admin_name || null,
        contact: f.contact || null,
        // Pending backend column branches.record_form_url — silently ignored until then
        record_form_url: f.record_form_url || null,
      }
      const { data, error } = await api.PUT('/api/branches/{branch_id}', {
        params: { path: { branch_id: branchId } },
        body,
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      setSavedAt(new Date().toLocaleTimeString())
      qc.invalidateQueries({ queryKey: ['branch', branchId] })
      qc.invalidateQueries({ queryKey: ['branches'] })
    },
  })

  if (isLoading) return <LoadingState />
  if (error) return <ErrorMessage>{String(error)}</ErrorMessage>

  const set = <K extends keyof Form>(k: K, v: Form[K]) => setForm((f) => ({ ...f, [k]: v }))

  // Crude Thailand bounding-box check for lat/lng (5°N-21°N, 97°E-106°E)
  const lat = form.latitude === '' ? null : Number(form.latitude)
  const lng = form.longitude === '' ? null : Number(form.longitude)
  const geoOutOfTH =
    (lat !== null && (Number.isNaN(lat) || lat < 5 || lat > 21)) ||
    (lng !== null && (Number.isNaN(lng) || lng < 97 || lng > 106))

  // me-ui served at /me-ui/ on same host; dev runs on :5174 so swap port
  const origin = window.location.origin.replace(/:5173$/, '')
  const memberLink = viewLink
    ? `${origin}/me-ui/br/${viewLink.branch_id}-${viewLink.view_secret}`
    : ''

  return (
    <div className="grid gap-4 max-w-3xl">
      <PageHeading title="Edit Branch" subtitle={<code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">{branchId}</code>} />

      <MemberLinkCard link={memberLink} />

      <Card>
        <CardBody>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              saveMut.mutate(form)
            }}
            className="grid gap-3"
          >
            <Field label="ชื่อสาขา *">
              <Input value={form.name} onChange={(e) => set('name', e.target.value)} required />
            </Field>
            <Field label="กลุ่ม (group_id)">
              <Input value={form.group_id} onChange={(e) => set('group_id', e.target.value)} placeholder="เช่น G24" />
            </Field>
            <Field label="จังหวัด">
              <Input value={form.province} onChange={(e) => set('province', e.target.value)} />
            </Field>
            <Field label="Province code">
              <Input value={form.province_code} onChange={(e) => set('province_code', e.target.value)} placeholder="เช่น TH-54" />
            </Field>
            <Field label="Latitude">
              <Input
                type="number"
                step="any"
                value={form.latitude}
                onChange={(e) => set('latitude', e.target.value)}
                placeholder="13.75"
              />
            </Field>
            <Field label="Longitude">
              <Input
                type="number"
                step="any"
                value={form.longitude}
                onChange={(e) => set('longitude', e.target.value)}
                placeholder="100.50"
              />
            </Field>
            {geoOutOfTH && (
              <div className="grid grid-cols-[160px_1fr] items-start gap-3">
                <span></span>
                <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                  ⚠ Lat/Lng อยู่นอกประเทศไทย (TH bbox: lat 5–21, lng 97–106)
                </div>
              </div>
            )}
            <Field label="ผู้ดูแลสาขา (admin_name)">
              <Input value={form.admin_name} onChange={(e) => set('admin_name', e.target.value)} />
            </Field>
            <Field label="Contact">
              <Input value={form.contact} onChange={(e) => set('contact', e.target.value)} placeholder="เบอร์โทร" />
            </Field>
            <Field label="Record Form URL">
              <Input
                type="url"
                value={form.record_form_url}
                onChange={(e) => set('record_form_url', e.target.value)}
                placeholder="https://forms.gle/... (Google Form ของสาขาให้ผู้เข้าร่วมกรอกบันทึก)"
              />
            </Field>
            <div className="grid grid-cols-[160px_1fr] items-start gap-3">
              <span></span>
              <div className="text-xs text-slate-500">
                ผู้เข้าร่วมจะเห็นปุ่มลิงก์นี้ใน me-ui dashboard ของตัวเอง
                {!data?.record_form_url && (
                  <span className="text-amber-700 ml-1">
                    · ⓘ รอ backend เพิ่ม column branches.record_form_url ก่อน save จะเก็บค่า
                  </span>
                )}
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 mt-3 pt-3 border-t border-slate-100 text-sm">
              <div>
                <div className="text-xs text-slate-500">Total minutes</div>
                <div className="font-bold tabular-nums">{Number(data?.total_minutes ?? 0).toLocaleString()}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500">Total records</div>
                <div className="font-bold tabular-nums">{Number(data?.total_records ?? 0).toLocaleString()}</div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3 mt-3 pt-3 border-t border-slate-100">
              <Button type="submit" disabled={saveMut.isPending}>
                {saveMut.isPending ? 'Saving…' : 'Save'}
              </Button>
              <Button type="button" variant="secondary" onClick={() => navigate({ to: '/branches' })}>
                Back
              </Button>
              {savedAt && <span className="text-sm text-green-700">บันทึกแล้ว {savedAt}</span>}
              {saveMut.error && <ErrorMessage>{String(saveMut.error)}</ErrorMessage>}
            </div>
          </form>
        </CardBody>
      </Card>
    </div>
  )
}

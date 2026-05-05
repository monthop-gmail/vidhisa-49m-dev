import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react'
import type { SortState } from '../lib/sort'

// ─── Button ───────────────────────────────────────────────────────

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'success' | 'ghost'
type ButtonSize = 'sm' | 'md'

const BTN_BASE =
  'inline-flex items-center justify-center font-medium rounded-md transition disabled:opacity-50 disabled:cursor-not-allowed'

const BTN_VARIANT: Record<ButtonVariant, string> = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700',
  secondary: 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50',
  danger: 'bg-red-600 text-white hover:bg-red-700',
  success: 'bg-green-600 text-white hover:bg-green-700',
  ghost: 'text-slate-600 hover:text-slate-900 hover:bg-slate-100',
}

const BTN_SIZE: Record<ButtonSize, string> = {
  sm: 'px-2.5 py-1 text-xs',
  md: 'px-4 py-2 text-sm',
}

export function Button({
  variant = 'primary',
  size = 'md',
  className = '',
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; size?: ButtonSize }) {
  return <button className={`${BTN_BASE} ${BTN_VARIANT[variant]} ${BTN_SIZE[size]} ${className}`} {...rest} />
}

// ─── Input / Select ───────────────────────────────────────────────

const INPUT_BASE =
  'w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-slate-100 disabled:text-slate-500'

export function Input({ className = '', ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`${INPUT_BASE} ${className}`} {...rest} />
}

export function Select({
  className = '',
  children,
  ...rest
}: SelectHTMLAttributes<HTMLSelectElement> & { children: ReactNode }) {
  return (
    <select className={`${INPUT_BASE} ${className}`} {...rest}>
      {children}
    </select>
  )
}

// ─── Field ────────────────────────────────────────────────────────

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="grid grid-cols-[160px_1fr] items-center gap-3">
      <span className="text-sm text-slate-600">{label}</span>
      <div>{children}</div>
    </label>
  )
}

// ─── Card ─────────────────────────────────────────────────────────

export function Card({ className = '', children }: { className?: string; children: ReactNode }) {
  return <div className={`bg-white border border-slate-200 rounded-lg shadow-sm ${className}`}>{children}</div>
}

export function CardBody({ className = '', children }: { className?: string; children: ReactNode }) {
  return <div className={`p-4 ${className}`}>{children}</div>
}

// ─── Badge ────────────────────────────────────────────────────────

type BadgeTone = 'gray' | 'blue' | 'green' | 'amber' | 'red' | 'purple'

const BADGE_TONE: Record<BadgeTone, string> = {
  gray: 'bg-slate-100 text-slate-700',
  blue: 'bg-blue-100 text-blue-800',
  green: 'bg-green-100 text-green-800',
  amber: 'bg-amber-100 text-amber-800',
  red: 'bg-red-100 text-red-800',
  purple: 'bg-purple-100 text-purple-800',
}

export function Badge({ tone = 'gray', children }: { tone?: BadgeTone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${BADGE_TONE[tone]}`}>
      {children}
    </span>
  )
}

const STATUS_TONE: Record<string, BadgeTone> = {
  pending: 'amber',
  approved: 'green',
  rejected: 'red',
  active: 'green',
  inactive: 'gray',
}

export function StatusBadge({ status }: { status: string }) {
  const tone: BadgeTone = STATUS_TONE[status] ?? 'gray'
  return <Badge tone={tone}>{status || '—'}</Badge>
}

// ─── Table ────────────────────────────────────────────────────────

export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto bg-white border border-slate-200 rounded-lg">
      <table className="w-full border-collapse">{children}</table>
    </div>
  )
}

export function Thead({ children }: { children: ReactNode }) {
  return <thead className="bg-slate-50">{children}</thead>
}

export function Tr({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <tr className={`hover:bg-slate-50 ${className}`}>{children}</tr>
}

export function Th({
  children,
  align = 'left',
}: {
  children?: ReactNode
  align?: 'left' | 'right' | 'center'
}) {
  const alignClass = align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left'
  return (
    <th className={`${alignClass} border-b border-slate-200 px-3 py-2.5 text-xs font-semibold text-slate-700 uppercase tracking-wide`}>
      {children}
    </th>
  )
}

export function Td({
  children,
  align = 'left',
  className = '',
}: {
  children?: ReactNode
  align?: 'left' | 'right' | 'center'
  className?: string
}) {
  const alignClass = align === 'right' ? 'text-right tabular-nums' : align === 'center' ? 'text-center' : 'text-left'
  return <td className={`${alignClass} border-b border-slate-100 px-3 py-2.5 text-sm ${className}`}>{children}</td>
}

// ─── SortableTh ───────────────────────────────────────────────────

export function SortableTh<K extends string>({
  children,
  align = 'left',
  sortKey,
  sort,
  onSort,
}: {
  children?: ReactNode
  align?: 'left' | 'right' | 'center'
  sortKey: K
  sort: SortState<K>
  onSort: (key: K) => void
}) {
  const alignClass = align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left'
  const active = sort?.key === sortKey
  const arrow = active ? (sort?.dir === 'asc' ? '↑' : '↓') : '↕'
  return (
    <th
      onClick={() => onSort(sortKey)}
      className={`${alignClass} border-b border-slate-200 px-3 py-2.5 text-xs font-semibold uppercase tracking-wide cursor-pointer select-none transition ${
        active ? 'text-blue-700 bg-blue-50' : 'text-slate-700 hover:bg-slate-100'
      }`}
    >
      <span className="inline-flex items-center gap-1">
        {children}
        <span className={`text-[10px] ${active ? 'opacity-100' : 'opacity-40'}`}>{arrow}</span>
      </span>
    </th>
  )
}

// ─── Page heading ─────────────────────────────────────────────────

export function PageHeading({
  title,
  subtitle,
  right,
}: {
  title: ReactNode
  subtitle?: ReactNode
  right?: ReactNode
}) {
  return (
    <div className="flex items-end justify-between gap-4 flex-wrap">
      <div>
        {subtitle && <div className="text-sm text-slate-500">{subtitle}</div>}
        <h1 className="text-2xl font-semibold text-slate-900 mt-0.5">{title}</h1>
      </div>
      {right && <div className="flex items-center gap-2">{right}</div>}
    </div>
  )
}

// ─── Empty / Error / Loading ──────────────────────────────────────

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="text-center text-sm text-slate-500 bg-slate-50 border border-dashed border-slate-300 rounded-md py-10 px-4">
      {children}
    </div>
  )
}

export function ErrorMessage({ children }: { children: ReactNode }) {
  return (
    <pre className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md p-3 whitespace-pre-wrap">
      {children}
    </pre>
  )
}

export function LoadingState() {
  return <div className="text-sm text-slate-500">Loading…</div>
}

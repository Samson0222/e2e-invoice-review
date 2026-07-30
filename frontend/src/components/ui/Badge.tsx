import type { HTMLAttributes } from 'react'

type BadgeTone = 'neutral' | 'error' | 'warning' | 'success'

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone
}

const tones: Record<BadgeTone, string> = {
  neutral: 'bg-zinc-100 text-zinc-600 border-zinc-200',
  error: 'bg-red-50 text-red-700 border-red-200',
  warning: 'bg-amber-50 text-amber-700 border-amber-200',
  success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
}

export function Badge({ className = '', tone = 'neutral', ...props }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${tones[tone]} ${className}`}
      {...props}
    />
  )
}

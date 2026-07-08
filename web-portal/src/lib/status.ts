import type { TaskStatus } from './types';

const TONE_CLASSES = {
  slate: 'bg-white/[0.04] text-slate-300 border-white/10',
  indigo: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/20',
  emerald: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20',
  amber: 'bg-amber-500/10 text-amber-300 border-amber-500/20',
  red: 'bg-red-500/10 text-red-300 border-red-500/20',
} as const;

export type Tone = keyof typeof TONE_CLASSES;

export function toneClass(tone: Tone): string {
  return TONE_CLASSES[tone];
}

export const TASK_STATUS_TONE: Record<TaskStatus, Tone> = {
  idle: 'slate',
  running: 'indigo',
  completed: 'emerald',
  stopped: 'amber',
  error: 'red',
};

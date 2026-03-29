import type { AuthLevel, ToolCategory } from './types';

export const AUTH_LEVEL_COLORS: Record<AuthLevel, { bg: string; text: string; border: string }> = {
  low:      { bg: 'bg-green-500/20',  text: 'text-green-400',  border: 'border-green-500/40' },
  medium:   { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/40' },
  high:     { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/40' },
  critical: { bg: 'bg-red-500/20',    text: 'text-red-400',    border: 'border-red-500/40' },
};

export const CATEGORY_LABELS: Record<ToolCategory, string> = {
  wifi:              'WiFi',
  network:           'Network',
  exploitation:      'Exploitation',
  post_exploitation: 'Post-Exploitation',
  password:          'Password',
  monitoring:        'Monitoring',
  ctf:               'CTF',
};

export const JOB_STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  pending:                { bg: 'bg-slate-600',  text: 'text-slate-200' },
  running:                { bg: 'bg-blue-600',   text: 'text-blue-100' },
  waiting_confirmation:   { bg: 'bg-amber-600',  text: 'text-amber-100' },
  confirmed:              { bg: 'bg-green-600',  text: 'text-green-100' },
  completed:              { bg: 'bg-green-600',  text: 'text-green-100' },
  failed:                 { bg: 'bg-red-600',    text: 'text-red-100' },
};

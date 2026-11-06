import { http } from '@/lib/http'

export interface AccountItem {
  name: string
  path: string
}

export interface AccountDetail extends AccountItem {
  content: string
}

export async function listAccounts(): Promise<AccountItem[]> {
  return await http('/api/accounts')
}

export async function getAccount(name: string): Promise<AccountDetail> {
  return await http(`/api/accounts/${encodeURIComponent(name)}`)
}

export async function createAccount(payload: { name: string; content: string }): Promise<AccountDetail> {
  return await http('/api/accounts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function updateAccount(name: string, content: string): Promise<AccountDetail> {
  return await http(`/api/accounts/${encodeURIComponent(name)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  })
}

export async function deleteAccount(name: string): Promise<{ message: string }> {
  return await http(`/api/accounts/${encodeURIComponent(name)}`, { method: 'DELETE' })
}

export interface AccountStatus {
  name: string
  valid: boolean
  status: 'valid' | 'expired' | 'risk_control' | 'missing_token' | 'missing_file' | 'invalid_file' | 'error'
  nick: string
  unb: string
  tracknick: string
  reason: string
  anti_bot_cookies: { x5sec: boolean; mtop_partitioned_detect: boolean }
  checked_at: string
}

export interface GuardTask {
  task_name: string
  consecutive_failures: number
  paused: boolean
  paused_until: string | null
  last_failure_at: string | null
  last_failure_reason: string | null
  last_success_at: string | null
}

export interface GuardAccount {
  account: string
  cooling_down: boolean
  cooldown_remaining_seconds: number
  reason: string | null
  trips: number
}

export interface GuardState {
  threshold: number
  pause_seconds: number
  tasks: GuardTask[]
  cooldown_seconds: number
  accounts: GuardAccount[]
}

export async function getAccountStatus(name: string): Promise<AccountStatus> {
  return await http(`/api/accounts/${encodeURIComponent(name)}/status`)
}

export async function getGuardState(): Promise<GuardState> {
  return await http('/api/accounts/guard')
}

export async function resetGuard(target: { taskName?: string; account?: string } = {}): Promise<{ message: string; reset: number }> {
  const body: Record<string, string> = {}
  if (target.taskName) body.task_name = target.taskName
  if (target.account) body.account = target.account
  return await http('/api/accounts/guard/reset', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export interface VerifyStatus {
  status: 'idle' | 'opening' | 'waiting' | 'solved' | 'closed' | 'timeout'
  account?: string
  message?: string
}

export async function startVerification(name: string): Promise<{ message: string; account: string }> {
  return await http(`/api/accounts/${encodeURIComponent(name)}/verify`, { method: 'POST' })
}

export async function getVerifyStatus(): Promise<VerifyStatus> {
  return await http('/api/accounts/verify/status')
}

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  listAccounts,
  getAccount,
  createAccount,
  updateAccount,
  deleteAccount,
  getAccountStatus,
  getGuardState,
  resetGuard,
  startVerification,
  getVerifyStatus,
  type VerifyStatus,
  type AccountItem,
  type AccountStatus,
  type GuardState,
} from '@/api/accounts'
import { Badge } from '@/components/ui/badge'
import { formatDateTime } from '@/i18n'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { toast } from '@/components/ui/toast'
const { t } = useI18n()

const accounts = ref<AccountItem[]>([])
const isLoading = ref(false)
const isSaving = ref(false)
const router = useRouter()

const isCreateDialogOpen = ref(false)
const isEditDialogOpen = ref(false)
const isDeleteDialogOpen = ref(false)

const newName = ref('')
const newContent = ref('')
const editName = ref('')
const editContent = ref('')
const deleteName = ref('')

type StatusEntry = { loading: boolean; result?: AccountStatus; error?: string }
const statuses = ref<Record<string, StatusEntry>>({})
const guard = ref<GuardState | null>(null)
const isGuardLoading = ref(false)
const isResettingGuard = ref(false)

async function checkStatus(name: string) {
  statuses.value = { ...statuses.value, [name]: { loading: true } }
  try {
    const result = await getAccountStatus(name)
    statuses.value = { ...statuses.value, [name]: { loading: false, result } }
  } catch (e) {
    statuses.value = { ...statuses.value, [name]: { loading: false, error: (e as Error).message } }
  }
}

async function checkAllStatuses() {
  for (const account of accounts.value) {
    await checkStatus(account.name)
  }
}

function statusLabel(entry?: StatusEntry): string {
  if (!entry) return t('accounts.status.notChecked')
  if (entry.loading) return t('accounts.status.checking')
  if (entry.error || !entry.result) return t('accounts.status.error')
  const { status, nick, tracknick } = entry.result
  const label = t(`accounts.status.${status}`)
  const name = nick || tracknick
  return status === 'valid' && name ? `${label} · ${name}` : label
}

function statusClass(entry?: StatusEntry): string {
  if (!entry || entry.loading) return 'bg-slate-100 text-slate-600'
  if (entry.result?.valid) return 'bg-emerald-50 text-emerald-700'
  if (entry.result?.status === 'risk_control') return 'bg-amber-50 text-amber-700'
  return 'bg-rose-50 text-rose-700'
}

function missingAntiBotCookie(entry?: StatusEntry): boolean {
  const cookies = entry?.result?.anti_bot_cookies
  return Boolean(entry?.result?.valid && cookies && !cookies.x5sec)
}

function statusHint(entry?: StatusEntry): string {
  if (!entry) return ''
  if (entry.error) return entry.error
  if (!entry.result) return ''
  const checked = formatDateTime(entry.result.checked_at, { dateStyle: 'short', timeStyle: 'medium' })
  return entry.result.valid
    ? t('accounts.status.checkedAt', { time: checked })
    : `${entry.result.reason || ''} (${checked})`.trim()
}

async function fetchGuard() {
  isGuardLoading.value = true
  try {
    guard.value = await getGuardState()
  } catch (e) {
    toast({ title: t('accounts.guard.loadFailed'), description: (e as Error).message, variant: 'destructive' })
  } finally {
    isGuardLoading.value = false
  }
}

const verify = ref<VerifyStatus>({ status: 'idle' })
const isVerifying = ref(false)
let verifyTimer: ReturnType<typeof setInterval> | null = null

function stopVerifyPolling() {
  if (verifyTimer) {
    clearInterval(verifyTimer)
    verifyTimer = null
  }
}

async function pollVerify() {
  try {
    verify.value = await getVerifyStatus()
  } catch {
    return
  }
  if (!['opening', 'waiting'].includes(verify.value.status)) {
    stopVerifyPolling()
    isVerifying.value = false
    if (verify.value.status === 'solved') {
      toast({ title: t('accounts.verify.solved') })
      await fetchGuard()
    }
  }
}

async function handleVerify(account: string) {
  isVerifying.value = true
  try {
    await startVerification(account)
    toast({ title: t('accounts.verify.opened') })
    stopVerifyPolling()
    verifyTimer = setInterval(pollVerify, 2000)
  } catch (e) {
    isVerifying.value = false
    toast({ title: t('accounts.verify.failed'), description: (e as Error).message, variant: 'destructive' })
  }
}

onBeforeUnmount(stopVerifyPolling)

async function handleResetGuard(target: { taskName?: string; account?: string } = {}) {
  isResettingGuard.value = true
  try {
    await resetGuard(target)
    toast({ title: t('accounts.guard.resetDone') })
    await fetchGuard()
  } catch (e) {
    toast({ title: t('accounts.guard.resetFailed'), description: (e as Error).message, variant: 'destructive' })
  } finally {
    isResettingGuard.value = false
  }
}

async function fetchAccounts() {
  isLoading.value = true
  try {
    accounts.value = await listAccounts()
  } catch (e) {
    toast({ title: t('accounts.toasts.loadFailed'), description: (e as Error).message, variant: 'destructive' })
  } finally {
    isLoading.value = false
  }
}

function openCreateDialog() {
  newName.value = ''
  newContent.value = ''
  isCreateDialogOpen.value = true
}

async function openEditDialog(name: string) {
  isSaving.value = true
  try {
    const detail = await getAccount(name)
    editName.value = detail.name
    editContent.value = detail.content
    isEditDialogOpen.value = true
  } catch (e) {
    toast({ title: t('accounts.toasts.loadContentFailed'), description: (e as Error).message, variant: 'destructive' })
  } finally {
    isSaving.value = false
  }
}

function openDeleteDialog(name: string) {
  deleteName.value = name
  isDeleteDialogOpen.value = true
}

function goCreateTask(name: string) {
  router.push({ path: '/tasks', query: { account: name, create: '1' } })
}

async function handleCreateAccount() {
  if (!newName.value.trim() || !newContent.value.trim()) {
    toast({ title: t('accounts.toasts.incomplete'), description: t('accounts.toasts.createDescriptionRequired'), variant: 'destructive' })
    return
  }
  isSaving.value = true
  try {
    await createAccount({ name: newName.value.trim(), content: newContent.value.trim() })
    toast({ title: t('accounts.toasts.created') })
    isCreateDialogOpen.value = false
    await fetchAccounts()
  } catch (e) {
    toast({ title: t('accounts.toasts.createFailed'), description: (e as Error).message, variant: 'destructive' })
  } finally {
    isSaving.value = false
  }
}

async function handleUpdateAccount() {
  if (!editContent.value.trim()) {
    toast({ title: t('accounts.toasts.contentRequired'), description: t('accounts.toasts.updateDescriptionRequired'), variant: 'destructive' })
    return
  }
  isSaving.value = true
  try {
    await updateAccount(editName.value, editContent.value.trim())
    toast({ title: t('accounts.toasts.updated') })
    isEditDialogOpen.value = false
    await fetchAccounts()
  } catch (e) {
    toast({ title: t('accounts.toasts.updateFailed'), description: (e as Error).message, variant: 'destructive' })
  } finally {
    isSaving.value = false
  }
}

async function handleDeleteAccount() {
  isSaving.value = true
  try {
    await deleteAccount(deleteName.value)
    toast({ title: t('accounts.toasts.deleted') })
    isDeleteDialogOpen.value = false
    await fetchAccounts()
  } catch (e) {
    toast({ title: t('accounts.toasts.deleteFailed'), description: (e as Error).message, variant: 'destructive' })
  } finally {
    isSaving.value = false
  }
}

onMounted(() => {
  void fetchAccounts()
  void fetchGuard()
})
</script>

<template>
  <div>
    <div class="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-800">{{ t('accounts.title') }}</h1>
        <p class="text-sm text-gray-500 mt-1">{{ t('accounts.description') }}</p>
      </div>
      <Button class="w-full sm:w-auto" @click="openCreateDialog">{{ t('accounts.add') }}</Button>
    </div>

    <Card class="app-surface mb-6 border-none">
      <CardHeader>
        <CardTitle>{{ t('accounts.cookieGuide.title') }}</CardTitle>
      </CardHeader>
      <CardContent class="text-sm text-gray-600">
        <ol class="list-decimal list-inside space-y-1">
          <li>
            {{ t('accounts.cookieGuide.step1Prefix') }}
            <a
              class="text-blue-600 hover:underline"
              href="https://chromewebstore.google.com/detail/xianyu-login-state-extrac/eidlpfjiodpigmfcahkmlenhppfklcoa"
              target="_blank"
              rel="noopener noreferrer"
            >{{ t('accounts.cookieGuide.extension') }}</a>
          </li>
          <li>
            {{ t('accounts.cookieGuide.step2Prefix') }}
            <a
              class="text-blue-600 hover:underline"
              href="https://www.goofish.com"
              target="_blank"
              rel="noopener noreferrer"
            >{{ t('accounts.cookieGuide.website') }}</a>
          </li>
          <li>{{ t('accounts.cookieGuide.step3') }}</li>
          <li>{{ t('accounts.cookieGuide.step4') }}</li>
          <li>{{ t('accounts.cookieGuide.step5') }}</li>
        </ol>
      </CardContent>
    </Card>

    <Card class="app-surface border-none">
      <CardHeader class="flex flex-row items-start justify-between gap-4 space-y-0">
        <div class="space-y-1.5">
          <CardTitle>{{ t('accounts.guard.title') }}</CardTitle>
          <CardDescription>{{ t('accounts.guard.description', { threshold: guard?.threshold ?? 3 }) }}</CardDescription>
        </div>
        <div class="flex shrink-0 gap-2">
          <Button size="sm" variant="outline" :disabled="isGuardLoading" @click="fetchGuard">{{ t('common.refresh') }}</Button>
          <Button size="sm" :disabled="isResettingGuard || (!guard?.tasks.length && !guard?.accounts.length)" @click="handleResetGuard()">{{ t('accounts.guard.resetAll') }}</Button>
        </div>
      </CardHeader>
      <CardContent>
        <div v-if="guard?.accounts.length" class="mb-4 space-y-2">
          <h4 class="text-sm font-semibold text-slate-700">{{ t('accounts.guard.accountsTitle') }}</h4>
          <ul class="divide-y divide-slate-100">
            <li v-for="item in guard.accounts" :key="item.account" class="flex flex-wrap items-center justify-between gap-3 py-2">
              <div class="min-w-0 space-y-0.5">
                <div class="flex flex-wrap items-center gap-2">
                  <span class="text-sm font-semibold text-slate-800">{{ item.account }}</span>
                  <Badge variant="outline" :class="item.cooling_down ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'">
                    {{ item.cooling_down
                      ? t('accounts.guard.accountCooling', { minutes: Math.ceil(item.cooldown_remaining_seconds / 60) })
                      : t('accounts.guard.accountReady') }}
                  </Badge>
                </div>
                <p v-if="item.cooling_down && item.reason" class="break-all text-xs text-slate-500">
                  {{ t('accounts.guard.lastError', { reason: item.reason }) }}
                </p>
              </div>
              <div class="flex flex-wrap items-center gap-2">
                <Button size="sm" :disabled="isVerifying" @click="handleVerify(item.account)">
                  {{ isVerifying ? t('accounts.verify.waiting') : t('accounts.verify.button') }}
                </Button>
                <Button size="sm" variant="outline" :disabled="isResettingGuard || !item.cooling_down" @click="handleResetGuard({ account: item.account })">
                  {{ t('accounts.guard.resetAccount') }}
                </Button>
              </div>
            </li>
          </ul>
        </div>
        <p v-if="verify.status !== 'idle'" class="mb-2 text-xs text-slate-600">
          {{ t(`accounts.verify.state.${verify.status}`) }}
        </p>
        <p class="mb-3 text-xs text-slate-500">{{ t('accounts.verify.hint') }}</p>
        <p class="mb-3 text-xs text-slate-500">{{ t('accounts.guard.localOnlyHint', { minutes: Math.round((guard?.cooldown_seconds ?? 1800) / 60) }) }}</p>
        <p v-if="!guard?.tasks.length" class="py-4 text-center text-sm text-muted-foreground">{{ t('accounts.guard.empty') }}</p>
        <ul v-else class="divide-y divide-slate-100">
          <li v-for="task in guard.tasks" :key="task.task_name" class="flex flex-wrap items-center justify-between gap-3 py-3">
            <div class="min-w-0 space-y-1">
              <div class="flex flex-wrap items-center gap-2">
                <span class="truncate text-sm font-semibold text-slate-800">{{ task.task_name }}</span>
                <Badge variant="outline" :class="task.paused ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'">
                  {{ task.paused ? t('accounts.guard.paused') : t('accounts.guard.active') }}
                </Badge>
                <span class="text-xs text-slate-500">{{ t('accounts.guard.failures', { count: task.consecutive_failures, threshold: guard.threshold }) }}</span>
              </div>
              <p v-if="task.paused && task.paused_until" class="text-xs text-amber-700">
                {{ t('accounts.guard.pausedUntil', { time: formatDateTime(task.paused_until, { dateStyle: 'short', timeStyle: 'short' }) }) }}
              </p>
              <p v-if="task.last_failure_reason" class="break-all text-xs text-slate-500">
                {{ t('accounts.guard.lastError', { reason: task.last_failure_reason }) }}
              </p>
            </div>
            <Button
              size="sm"
              variant="outline"
              :disabled="isResettingGuard || (!task.paused && task.consecutive_failures === 0)"
              @click="handleResetGuard({ taskName: task.task_name })"
            >
              {{ t('accounts.guard.resetTask') }}
            </Button>
          </li>
        </ul>
      </CardContent>
    </Card>

    <Card class="app-surface border-none">
      <CardHeader class="flex flex-row items-start justify-between gap-4 space-y-0">
        <div class="space-y-1.5">
          <CardTitle>{{ t('accounts.list.title') }}</CardTitle>
          <CardDescription>{{ t('accounts.list.description') }}</CardDescription>
        </div>
        <Button size="sm" variant="outline" class="shrink-0" :disabled="!accounts.length" @click="checkAllStatuses">{{ t('accounts.status.checkAll') }}</Button>
      </CardHeader>
      <CardContent>
        <div class="space-y-4 md:hidden">
          <div v-if="isLoading" class="py-10 text-center text-sm text-muted-foreground">{{ t('common.loading') }}</div>
          <div v-else-if="accounts.length === 0" class="py-10 text-center text-sm text-muted-foreground">{{ t('accounts.list.empty') }}</div>
          <article
            v-else
            v-for="account in accounts"
            :key="account.name"
            class="app-surface-subtle p-4"
          >
            <div class="space-y-2">
              <div class="flex items-center justify-between gap-3">
                <h3 class="truncate text-base font-semibold text-slate-900">{{ account.name }}</h3>
                <Button size="sm" variant="outline" @click="goCreateTask(account.name)">{{ t('accounts.list.createTask') }}</Button>
              </div>
              <p class="break-all text-sm text-slate-500">{{ account.path }}</p>
              <div class="flex flex-wrap items-center gap-2">
                <Badge variant="outline" :class="statusClass(statuses[account.name])">{{ statusLabel(statuses[account.name]) }}</Badge>
                <span v-if="statusHint(statuses[account.name])" class="break-all text-xs text-slate-500">{{ statusHint(statuses[account.name]) }}</span>
              </div>
              <p v-if="missingAntiBotCookie(statuses[account.name])" class="text-xs text-amber-700">{{ t('accounts.status.noX5sec') }}</p>
            </div>
            <div class="mt-4 flex flex-wrap gap-2">
              <Button size="sm" variant="outline" class="flex-1 min-w-[120px]" :disabled="statuses[account.name]?.loading" @click="checkStatus(account.name)">{{ t('accounts.status.check') }}</Button>
              <Button size="sm" variant="outline" class="flex-1 min-w-[120px]" @click="openEditDialog(account.name)">{{ t('accounts.list.update') }}</Button>
              <Button size="sm" variant="destructive" class="flex-1 min-w-[120px]" @click="openDeleteDialog(account.name)">{{ t('accounts.list.delete') }}</Button>
            </div>
          </article>
        </div>

        <div class="hidden md:block">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{{ t('accounts.list.name') }}</TableHead>
                <TableHead>{{ t('accounts.list.file') }}</TableHead>
                <TableHead>{{ t('accounts.status.column') }}</TableHead>
                <TableHead class="text-right">{{ t('accounts.list.actions') }}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-if="isLoading">
                <TableCell colspan="4" class="h-20 text-center text-muted-foreground">{{ t('common.loading') }}</TableCell>
              </TableRow>
              <TableRow v-else-if="accounts.length === 0">
                <TableCell colspan="4" class="h-20 text-center text-muted-foreground">{{ t('accounts.list.empty') }}</TableCell>
              </TableRow>
              <TableRow v-else v-for="account in accounts" :key="account.name">
                <TableCell class="font-medium">{{ account.name }}</TableCell>
                <TableCell class="text-sm text-gray-500">{{ account.path }}</TableCell>
                <TableCell>
                  <div class="space-y-1">
                    <Badge variant="outline" :class="statusClass(statuses[account.name])">{{ statusLabel(statuses[account.name]) }}</Badge>
                    <p v-if="statusHint(statuses[account.name])" class="max-w-[260px] break-all text-xs text-slate-500">{{ statusHint(statuses[account.name]) }}</p>
                    <p v-if="missingAntiBotCookie(statuses[account.name])" class="max-w-[260px] text-xs text-amber-700">{{ t('accounts.status.noX5sec') }}</p>
                  </div>
                </TableCell>
                <TableCell class="text-right">
                  <div class="flex justify-end gap-2">
                    <Button size="sm" variant="outline" :disabled="statuses[account.name]?.loading" @click="checkStatus(account.name)">{{ t('accounts.status.check') }}</Button>
                    <Button size="sm" variant="outline" @click="goCreateTask(account.name)">{{ t('accounts.list.createTask') }}</Button>
                    <Button size="sm" variant="outline" @click="openEditDialog(account.name)">{{ t('accounts.list.update') }}</Button>
                    <Button size="sm" variant="destructive" @click="openDeleteDialog(account.name)">{{ t('accounts.list.delete') }}</Button>
                  </div>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>

    <Dialog v-model:open="isCreateDialogOpen">
      <DialogContent class="sm:max-w-[700px]">
        <DialogHeader>
          <DialogTitle>{{ t('accounts.createDialog.title') }}</DialogTitle>
          <DialogDescription>{{ t('accounts.createDialog.description') }}</DialogDescription>
        </DialogHeader>
        <div class="space-y-4">
          <div class="grid gap-2">
            <Label>{{ t('accounts.createDialog.name') }}</Label>
            <Input v-model="newName" :placeholder="t('accounts.createDialog.namePlaceholder')" />
          </div>
          <div class="grid gap-2">
            <Label>{{ t('accounts.createDialog.jsonContent') }}</Label>
            <Textarea v-model="newContent" class="min-h-[200px]" :placeholder="t('accounts.createDialog.jsonPlaceholder')" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="isCreateDialogOpen = false">{{ t('common.cancel') }}</Button>
          <Button :disabled="isSaving" @click="handleCreateAccount">
            {{ isSaving ? t('common.saving') : t('common.save') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="isEditDialogOpen">
      <DialogContent class="sm:max-w-[700px]">
        <DialogHeader>
          <DialogTitle>{{ t('accounts.editDialog.title', { name: editName }) }}</DialogTitle>
          <DialogDescription>{{ t('accounts.editDialog.description') }}</DialogDescription>
        </DialogHeader>
        <div class="space-y-4">
          <div class="grid gap-2">
            <Label>{{ t('accounts.createDialog.jsonContent') }}</Label>
            <Textarea v-model="editContent" class="min-h-[200px]" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="isEditDialogOpen = false">{{ t('common.cancel') }}</Button>
          <Button :disabled="isSaving" @click="handleUpdateAccount">
            {{ isSaving ? t('common.saving') : t('common.save') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="isDeleteDialogOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{{ t('accounts.deleteDialog.title') }}</DialogTitle>
          <DialogDescription>{{ t('accounts.deleteDialog.description', { name: deleteName }) }}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" @click="isDeleteDialogOpen = false">{{ t('common.cancel') }}</Button>
          <Button variant="destructive" :disabled="isSaving" @click="handleDeleteAccount">
            {{ isSaving ? t('accounts.deleteDialog.deleting') : t('accounts.list.delete') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

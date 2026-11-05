import { computed, watch } from 'vue'
import { createI18n, useI18n } from 'vue-i18n'
import zhCN from '@/i18n/messages/zh-CN'
import enUS from '@/i18n/messages/en-US'
import ptBR from '@/i18n/messages/pt-BR'
import { BACKEND_MESSAGE_RULES } from '@/i18n/backendMessages'
import { LOG_LINE_RULES } from '@/i18n/logLines'

export type AppLocale = 'zh-CN' | 'en-US' | 'pt-BR'

const LOCALE_STORAGE_KEY = 'app_locale'
const DEFAULT_LOCALE: AppLocale = 'zh-CN'
const SUPPORTED_LOCALES: AppLocale[] = ['zh-CN', 'en-US', 'pt-BR']

function resolveInitialLocale(): AppLocale {
  const saved = localStorage.getItem(LOCALE_STORAGE_KEY)
  if (saved && SUPPORTED_LOCALES.includes(saved as AppLocale)) {
    return saved as AppLocale
  }
  const browserLocale = navigator.language.toLowerCase()
  if (browserLocale.startsWith('zh')) return 'zh-CN'
  if (browserLocale.startsWith('pt')) return 'pt-BR'
  return 'en-US'
}

export const i18n = createI18n({
  legacy: false,
  locale: resolveInitialLocale(),
  fallbackLocale: DEFAULT_LOCALE,
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS,
    'pt-BR': ptBR,
  },
})

export function setLocale(locale: AppLocale) {
  i18n.global.locale.value = locale
}

export function useLocale() {
  const { locale } = useI18n()
  const currentLocale = computed(() => locale.value as AppLocale)

  function toggleLocale(nextLocale: AppLocale) {
    locale.value = nextLocale
  }

  return {
    locale: currentLocale,
    toggleLocale,
    supportedLocales: SUPPORTED_LOCALES,
  }
}

export function t(key: string, params?: Record<string, unknown>) {
  return params ? i18n.global.t(key, params) : i18n.global.t(key)
}

export function translateBackendMessage(text: string | null | undefined): string {
  if (!text) return text ?? ''
  for (const rule of BACKEND_MESSAGE_RULES) {
    const match = rule.re.exec(text)
    if (match) return t(`backend.${rule.key}`, { ...(match.groups ?? {}) })
  }
  return text
}

const CJK_RE = /[\u4e00-\u9fff]/
const LOG_PREFIX_RE = /^(\s*(?:\[ ?\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]\s*)?)(.*)$/
const logLineCache = new Map<string, string>()

function translateLogLine(line: string): string {
  if (!CJK_RE.test(line)) return line
  const key = `${i18n.global.locale.value}\u0000${line}`
  const cached = logLineCache.get(key)
  if (cached !== undefined) return cached
  let result = line
  const parts = LOG_PREFIX_RE.exec(line)
  if (parts) {
    for (const rule of LOG_LINE_RULES) {
      const match = rule.re.exec(parts[2] ?? '')
      if (match) {
        result = (parts[1] ?? '') + t(`logLines.${rule.key}`, { ...(match.groups ?? {}) })
        break
      }
    }
  }
  if (logLineCache.size > 5000) logLineCache.clear()
  logLineCache.set(key, result)
  return result
}

// Translates scraper log lines for display only; the log files themselves are not modified.
export function translateLogText(text: string | null | undefined): string {
  if (!text) return text ?? ''
  return text.split('\n').map(translateLogLine).join('\n')
}

export function formatNumber(value: number, options?: Intl.NumberFormatOptions) {
  return new Intl.NumberFormat(i18n.global.locale.value, options).format(value)
}

export function formatDateTime(
  value: string | Date,
  options: Intl.DateTimeFormatOptions = {},
) {
  const date = value instanceof Date ? value : new Date(value)
  return new Intl.DateTimeFormat(i18n.global.locale.value, options).format(date)
}

export function formatRelativeTimeFromNow(value: string | null | undefined) {
  if (!value) return t('time.justNow')
  const timestamp = new Date(value).getTime()
  if (Number.isNaN(timestamp)) return t('time.justNow')
  const diffMinutes = Math.max(1, Math.round((Date.now() - timestamp) / 60000))
  if (diffMinutes < 60) return t('time.minutesAgo', { count: diffMinutes })
  const diffHours = Math.round(diffMinutes / 60)
  if (diffHours < 24) return t('time.hoursAgo', { count: diffHours })
  const diffDays = Math.round(diffHours / 24)
  return t('time.daysAgo', { count: diffDays })
}

watch(
  () => i18n.global.locale.value,
  (locale) => {
    localStorage.setItem(LOCALE_STORAGE_KEY, locale)
    document.documentElement.lang = locale
  },
  { immediate: true },
)

import type { TFunction } from 'i18next'
import { ApiError } from '@/api/client'

/** Human message for an error: translated by code when we have a key, else the server message. */
export function errorMessage(err: unknown, t: TFunction): string {
  if (err instanceof ApiError) {
    const key = `errors.${err.code}`
    const tr = t(key, { defaultValue: '' })
    if (tr) return tr
    if (err.code === 'network.unreachable') return t('errors.network.unreachable')
    return err.message || t('errors.generic')
  }
  if (err instanceof Error) return err.message
  return t('errors.generic')
}

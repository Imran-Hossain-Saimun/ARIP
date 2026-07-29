import { api } from '@/lib/api'
import type { AppSettingOut } from './types'

export function listSettings() {
  return api.get<AppSettingOut[]>('/v1/settings')
}

export function updateSetting(key: string, value: Record<string, unknown>) {
  return api.put<AppSettingOut>(`/v1/settings/${key}`, { value })
}

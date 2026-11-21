import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import '@/i18n'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  try {
    sessionStorage.clear()
    localStorage.clear()
  } catch {
    /* storage unavailable */
  }
})

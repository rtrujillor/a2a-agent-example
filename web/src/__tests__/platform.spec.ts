import { describe, expect, it } from 'vitest'

import { isApplePlatform } from '@/lib/platform'

const nav = (platform: string, uaPlatform?: string) =>
  ({
    platform,
    ...(uaPlatform === undefined ? {} : { userAgentData: { platform: uaPlatform } }),
  }) as unknown as Navigator

describe('isApplePlatform', () => {
  it.each(['MacIntel', 'iPhone', 'iPad'])('is true for %s', (platform) => {
    expect(isApplePlatform(nav(platform))).toBe(true)
  })

  it.each(['Win32', 'Linux x86_64', ''])('is false for %j', (platform) => {
    expect(isApplePlatform(nav(platform))).toBe(false)
  })

  it('prefers userAgentData when available', () => {
    expect(isApplePlatform(nav('', 'macOS'))).toBe(true)
    expect(isApplePlatform(nav('MacIntel', 'Windows'))).toBe(false)
  })
})

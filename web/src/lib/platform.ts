// `navigator.userAgentData` is not in TypeScript's DOM types yet.
type NavigatorWithUAData = Navigator & { userAgentData?: { platform?: string } }

/** True on macOS, iOS, and iPadOS, where the submit shortcut uses ⌘ instead of Ctrl. */
export function isApplePlatform(nav: Navigator | undefined = globalThis.navigator): boolean {
  if (!nav) return false
  const platform = (nav as NavigatorWithUAData).userAgentData?.platform ?? nav.platform ?? ''
  return /mac|iphone|ipad|ipod/i.test(platform)
}

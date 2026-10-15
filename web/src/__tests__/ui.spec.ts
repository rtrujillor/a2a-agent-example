import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { h } from 'vue'

import SourceTypeBadge from '@/components/SourceTypeBadge.vue'
import { Alert } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
import { Spinner } from '@/components/ui/spinner'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import type { SourceType } from '@/types/research'

describe('Skeleton', () => {
  it('renders a placeholder that pulses only when motion is allowed', () => {
    const skeleton = mount(Skeleton)
    expect(skeleton.attributes('data-slot')).toBe('skeleton')
    expect(skeleton.classes()).toContain('motion-safe:animate-pulse')
  })
})

describe('Spinner', () => {
  it('announces loading in Spanish', () => {
    const spinner = mount(Spinner)
    expect(spinner.attributes('role')).toBe('status')
    expect(spinner.attributes('aria-label')).toBe('Cargando')
  })
})

describe('Tooltip', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('opens when its trigger receives keyboard focus', async () => {
    // jsdom has no ResizeObserver; Reka UI measures the floating content with it.
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe() {}
        unobserve() {}
        disconnect() {}
      },
    )
    const Example = () =>
      h(TooltipProvider, () =>
        h(Tooltip, () => [
          h(TooltipTrigger, () => 'Fuente'),
          h(TooltipContent, () => 'Instituto Nacional de Estadística'),
        ]),
      )
    const wrapper = mount(Example, { attachTo: document.body })
    await wrapper.find('button').trigger('focus')
    await flushPromises()

    expect(document.body.textContent).toContain('Instituto Nacional de Estadística')
    wrapper.unmount()
  })
})

describe('SourceTypeBadge', () => {
  const cases: [SourceType, string][] = [
    ['official', 'Oficial'],
    ['media', 'Medio'],
    ['market', 'Mercado'],
    ['other', 'Otra'],
  ]

  it.each(cases)('shows a text label and its own style for %s', (type, label) => {
    const badge = mount(SourceTypeBadge, { props: { type } })
    expect(badge.text()).toBe(label)
    expect(badge.classes()).toContain(`bg-source-${type}`)
  })

  it('looks the same for two citations of the same type', () => {
    const a = mount(SourceTypeBadge, { props: { type: 'media' } })
    const b = mount(SourceTypeBadge, { props: { type: 'media' } })
    expect(a.classes()).toEqual(b.classes())
    expect(a.text()).toBe(b.text())
  })
})

describe('Alert', () => {
  it('styles limitation notices differently from errors', () => {
    const notice = mount(Alert, { props: { variant: 'notice' } })
    const error = mount(Alert, { props: { variant: 'destructive' } })
    expect(notice.classes()).toContain('bg-notice')
    expect(error.classes()).toContain('text-destructive')
    expect(notice.classes()).not.toContain('text-destructive')
  })
})

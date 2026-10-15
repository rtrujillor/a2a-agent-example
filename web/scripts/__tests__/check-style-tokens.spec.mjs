import { describe, expect, it } from 'vitest'

import { checkSource } from '../check-style-tokens.mjs'

const vue = (template, style = '') =>
  `<script setup lang="ts">\nconst href = 'https://example.org/#abc'\n</script>\n\n<template>\n${template}\n</template>\n${style}`

describe('check-style-tokens', () => {
  it('rejects a hex color in a style block with file and line', () => {
    const source = vue('  <p class="note">x</p>', '<style scoped>\n.note { color: #1d4ed8; }\n</style>')
    expect(checkSource('src/A.vue', source)).toEqual(['src/A.vue:9: raw hex color #1d4ed8'])
  })

  it('rejects an arbitrary color value in a class', () => {
    const problems = checkSource('src/B.vue', vue('  <div class="bg-[#fff]"></div>'))
    expect(problems).toContain('src/B.vue:6: arbitrary value with raw literal bg-[#fff]')
  })

  it('rejects an arbitrary length value in a class', () => {
    expect(checkSource('src/C.vue', vue('  <div class="p-[13px]"></div>'))).toEqual([
      'src/C.vue:6: arbitrary value with raw literal p-[13px]',
    ])
  })

  it('rejects raw values inside strings in script code', () => {
    expect(checkSource('src/d.ts', "export const v = cva('text-[oklch(0.5_0_0)]')")).toEqual([
      'src/d.ts:1: raw color function oklch(',
      'src/d.ts:1: arbitrary value with raw literal text-[oklch(0.5_0_0)]',
    ])
  })

  it('accepts token classes, variable references, and attribute variants', () => {
    const template =
      '  <div class="bg-primary text-primary-foreground h-[var(--x)] data-[state=open]:bg-accent"></div>'
    expect(checkSource('src/E.vue', vue(template))).toEqual([])
  })

  it('ignores URL fragments and lines marked as allowed', () => {
    const source = "const a = 'https://ine.es/#fff'\nconst b = '#abc' // style-tokens-allow"
    expect(checkSource('src/f.ts', source)).toEqual([])
  })
})

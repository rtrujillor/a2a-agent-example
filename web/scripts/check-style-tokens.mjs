// Rejects raw style values in components: hex colors, color functions, and
// Tailwind arbitrary values with raw literals. Tokens live in src/styles/ only.
// Exceptions: add `style-tokens-allow` as a comment on the offending line.
import { readdirSync, readFileSync } from 'node:fs'
import { join, relative, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const ALLOW = 'style-tokens-allow'
// Not preceded by a word char, `/` or `&`, which keeps URL fragments and entities out.
const HEX = /(?<![\w/&])#(?:[0-9a-f]{8}|[0-9a-f]{6}|[0-9a-f]{3,4})(?![\w-])/gi
const COLOR_FN = /\b(?:rgba?|hsla?|oklch|oklab)\(/gi
// `utility-[value]` not followed by `:` (that would be a variant like `data-[state=open]:`).
const ARBITRARY = /[\w-]+-\[([^\]\s]+)\](?!:)/g
const STRING = /'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*"|`(?:[^`\\]|\\.)*`/g

/** True when an arbitrary value holds a raw literal once `var(--…)` references are removed. */
function hasRawLiteral(value) {
  const rest = value.replace(/var\(--[\w-]+\)/g, '')
  return /\d|#|\b(?:rgba?|hsla?|oklch|oklab)\(/i.test(rest)
}

function checkText(text, push) {
  for (const m of text.matchAll(HEX)) push(`raw hex color ${m[0]}`)
  for (const m of text.matchAll(COLOR_FN)) push(`raw color function ${m[0]}`)
  for (const m of text.matchAll(ARBITRARY)) {
    if (hasRawLiteral(m[1])) push(`arbitrary value with raw literal ${m[0]}`)
  }
}

/**
 * Checks one file's source. In `<template>` and `<style>` every line is a style
 * context; in script code (`.ts`, `<script>`) only string literals are.
 * @param {string} file path used in messages
 * @param {string} source file contents
 * @returns {string[]} `file:line: message` entries
 */
export function checkSource(file, source) {
  const problems = []
  let section = file.endsWith('.vue') ? 'markup' : 'script'
  source.split('\n').forEach((line, index) => {
    if (file.endsWith('.vue')) {
      if (/^<script\b/.test(line)) section = 'script'
      else if (line.startsWith('</script>')) section = 'markup'
    }
    if (line.includes(ALLOW)) return
    const push = (message) => problems.push(`${file}:${index + 1}: ${message}`)
    if (section === 'script') {
      for (const m of line.matchAll(STRING)) checkText(m[0], push)
    } else {
      checkText(line, push)
    }
  })
  return problems
}

function* sourceFiles(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name)
    if (entry.isDirectory()) yield* sourceFiles(path)
    else if (/\.(vue|ts)$/.test(entry.name)) yield path
  }
}

/** Checks every `.vue` and `.ts` file under `srcDir`, skipping `srcDir/styles/`. */
export function checkDirectory(srcDir) {
  const problems = []
  const stylesDir = join(srcDir, 'styles') + sep
  for (const path of sourceFiles(srcDir)) {
    if (path.startsWith(stylesDir)) continue
    problems.push(...checkSource(relative(process.cwd(), path), readFileSync(path, 'utf8')))
  }
  return problems
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const problems = checkDirectory(fileURLToPath(new URL('../src', import.meta.url)))
  for (const problem of problems) console.error(problem)
  if (problems.length > 0) {
    console.error(`\n${problems.length} raw style value(s). Use tokens from src/styles/main.css.`)
    process.exit(1)
  }
}

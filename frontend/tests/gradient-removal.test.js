import test from 'node:test'
import assert from 'node:assert/strict'
import { readdir, readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendDirectory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const checkedExtensions = new Set(['.css', '.html', '.js', '.svg', '.vue'])
const forbiddenPatterns = [
  ['CSS gradient function', /(?:repeating-)?(?:linear|radial|conic)-gradient\s*\(/i],
  ['Tailwind gradient utility', /\bbg-gradient-to-[a-z]+\b/i],
  ['SVG gradient definition', /<(?:linear|radial)Gradient\b/i],
  ['SVG gradient reference', /url\(\s*#[^)]*gradient/i],
  ['Canvas gradient API', /\b(?:create(?:Linear|Radial|Conic)Gradient|CanvasGradient|addColorStop)\b/i],
]

async function sourceFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true })
  const files = []

  for (const entry of entries) {
    const entryPath = path.join(directory, entry.name)
    if (entry.isDirectory()) files.push(...await sourceFiles(entryPath))
    else if (checkedExtensions.has(path.extname(entry.name))) files.push(entryPath)
  }

  return files
}

test('frontend source and SVG assets contain no gradient implementations', async () => {
  const files = [
    path.join(frontendDirectory, 'index.html'),
    ...await sourceFiles(path.join(frontendDirectory, 'src')),
    ...await sourceFiles(path.join(frontendDirectory, 'public')),
  ]

  for (const file of files) {
    const source = await readFile(file, 'utf8')
    for (const [label, pattern] of forbiddenPatterns) {
      assert.doesNotMatch(source, pattern, `${label} found in ${path.relative(frontendDirectory, file)}`)
    }
  }
})

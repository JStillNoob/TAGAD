import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import { paginationQuery } from '../src/pagination.js'

test('pagination query omits empty filters and encodes populated values', () => {
  assert.equal(
    paginationQuery({ page: 2, search: 'data structures', role: '' }),
    '?page=2&search=data+structures',
  )
})

test('growing desktop lists render shared pagination controls', () => {
  for (const file of [
    'UserManagementView.vue',
    'StudentsView.vue',
    'ReportsView.vue',
    'SessionView.vue',
    'AnalyticsView.vue',
  ]) {
    const source = readFileSync(new URL(`../src/views/${file}`, import.meta.url), 'utf8')
    assert.match(source, /PaginationControls/)
  }

  const classesSource = readFileSync(new URL('../src/views/StudentsView.vue', import.meta.url), 'utf8')
  const sessionsSource = readFileSync(new URL('../src/views/SessionView.vue', import.meta.url), 'utf8')
  assert.ok((classesSource.match(/<PaginationControls/g) || []).length >= 3)
  assert.ok((sessionsSource.match(/<PaginationControls/g) || []).length >= 3)
  assert.doesNotMatch(sessionsSource, /sessions\.slice\(0, 5\)/)
})

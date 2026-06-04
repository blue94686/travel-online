import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const source = fs.readFileSync(path.resolve('src/pages/admin/AdminOperationsPage.jsx'), 'utf8')

assert.match(source, /admin-ops-layout/)
assert.match(source, /admin-ops-primary/)
assert.match(source, /待处理/)
assert.match(source, /景区资源检索/)
assert.equal(source.includes('Math.random'), false, 'admin dashboard should not use random trend data')

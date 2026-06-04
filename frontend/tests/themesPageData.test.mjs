import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const source = fs.readFileSync(path.resolve('src/pages/ThemesPage.jsx'), 'utf8')

assert.match(source, /apiThemes/)
assert.match(source, /theme\.description/)
assert.match(source, /theme\.keywords/)
assert.match(source, /theme\.season/)
assert.match(source, /theme\.audience/)
assert.equal(source.includes('数据库统计中'), false)

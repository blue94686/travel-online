import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const read = file => fs.readFileSync(path.resolve(file), 'utf8')

const databasePage = read('src/pages/admin/AdminDatabasePage.jsx')
const layoutPage = read('src/pages/admin/AdminLayoutPage.jsx')
const systemPage = read('src/pages/admin/AdminSystemPage.jsx')
const automationPage = read('src/pages/admin/AdminAutomationPage.jsx')
const styles = read('src/styles/pages.css')

assert.match(databasePage, /admin-database-console/)
assert.match(databasePage, /admin-code-editor/)
assert.match(databasePage, /quickQueries/)
assert.match(databasePage, /运行查询 \(Ctrl\+Enter\)/)

assert.match(layoutPage, /admin-layout-workbench/)
assert.match(layoutPage, /admin-editor-grid/)
assert.match(layoutPage, /admin-module-card/)
assert.match(layoutPage, /发布生效/)

assert.match(systemPage, /admin-system-console/)
assert.match(systemPage, /admin-health-overview/)
assert.match(systemPage, /admin-system-tabs/)

assert.match(automationPage, /admin-automation-console/)
assert.match(automationPage, /mergedEntries/)
assert.match(automationPage, /AI 管理/)
assert.match(automationPage, /API 接入/)
assert.match(automationPage, /admin-toggle-list/)

assert.match(styles, /\.admin-command-hero/)
assert.match(styles, /\.admin-status-strip/)
assert.match(styles, /\.admin-merged-entry-grid/)
assert.match(styles, /\.admin-toggle-list/)
assert.match(styles, /\.admin-console-layout/)
assert.match(styles, /\.admin-editor-grid/)
assert.match(styles, /\.admin-system-tabs/)

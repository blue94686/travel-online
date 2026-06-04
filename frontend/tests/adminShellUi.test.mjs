import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const sidebar = fs.readFileSync(path.resolve('src/components/admin/AdminSidebar.jsx'), 'utf8')
const topbar = fs.readFileSync(path.resolve('src/components/admin/AdminTopbar.jsx'), 'utf8')
const css = fs.readFileSync(path.resolve('src/styles/pages.css'), 'utf8')

assert.match(sidebar, /navGroups/)
assert.match(sidebar, /后台功能/)
assert.match(sidebar, /内容运营/)
assert.match(sidebar, /数据资产/)
assert.match(sidebar, /页面编排/)
assert.match(sidebar, /自动化与服务/)
assert.match(sidebar, /系统与安全/)
assert.match(sidebar, /admin-sidebar-health/)
assert.match(sidebar, /className=\{\(\) =>/)
assert.doesNotMatch(sidebar, /景区管理/)
assert.doesNotMatch(sidebar, /图片管理/)

assert.match(topbar, /roleLabelMap/)
assert.match(topbar, /commandItems/)
assert.match(topbar, /filteredCommands/)
assert.match(topbar, /admin-command-palette/)
assert.match(topbar, /admin-notice-popover/)
assert.match(topbar, /admin-help-popover/)
assert.match(topbar, /管理员/)
assert.match(topbar, /自动化与服务/)
assert.match(topbar, /admin-topbar-meta/)

assert.match(css, /admin-shell-polish/)
assert.match(css, /admin-topbar-meta/)
assert.match(css, /admin-command-palette/)
assert.match(css, /admin-popover/)
assert.match(css, /admin-help-grid/)
assert.match(css, /admin-sidebar-health/)
assert.match(css, /admin-merged-entry-grid/)
assert.match(css, /@media \(max-width: 1280px\)/)

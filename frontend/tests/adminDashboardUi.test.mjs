import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const source = fs.readFileSync(path.resolve('src/pages/admin/AdminOperationsPage.jsx'), 'utf8')

for (const requiredText of [
  '管理总览',
  '数据服务状态',
  'AI 服务状态',
  'AI 资源使用',
  '快捷操作',
  '待审核图片',
  '待审核评论',
  '最近同步任务',
  '系统日志',
  '数据治理',
]) {
  assert.equal(source.includes(requiredText), true, `${requiredText} should be rendered on admin dashboard`)
}

for (const requiredClass of [
  'admin-control-room',
  'admin-control-kpis',
  'admin-health-ring',
  'admin-service-matrix',
  'admin-review-board',
]) {
  assert.equal(source.includes(requiredClass), true, `${requiredClass} should exist`)
}

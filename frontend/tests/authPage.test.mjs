import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const source = fs.readFileSync(path.resolve('src/pages/AuthPage.jsx'), 'utf8')

assert.match(source, /sendCode/)
assert.match(source, /login/)
assert.match(source, /账号密码登录/)
assert.match(source, /账号密码注册/)
assert.match(source, /登录\s*<\/button>/)
assert.match(source, /注册\s*<\/button>/)
assert.match(source, /type="password"/)
assert.match(source, /register/)
assert.match(source, /mode === 'register' &&/)

for (const removedText of [
  '其他登录方式',
  '立即注册',
  '已有账号',
  '昵称',
  '用户服务协议',
  '账户安全提示',
  '注册后您将获得',
  '演示用'
]) {
  assert.equal(source.includes(removedText), false, `${removedText} should not appear on auth page`)
}

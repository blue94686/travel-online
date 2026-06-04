import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const read = file => fs.readFileSync(path.resolve(file), 'utf8')

const home = read('src/pages/HomePage.jsx')
const globalCss = read('src/styles/global.css')
const layoutCss = read('src/styles/layout.css')
const pagesCss = read('src/styles/pages.css')

assert.match(home, /home-inspiration-panel/)
assert.match(home, /home-guide-grid/)
assert.match(home, /home-theme-card/)
assert.match(home, /home-live-grid/)
assert.match(home, /home-tools-panel/)
assert.doesNotMatch(home, /onMouseEnter=\{/)

assert.match(globalCss, /radial-gradient\(circle at 12% 10%/)
assert.match(globalCss, /\.primary-btn:hover/)

assert.match(layoutCss, /\.site-nav nav a::after/)
assert.match(layoutCss, /linear-gradient\(135deg, #075985, var\(--color-primary\)\)/)

assert.match(pagesCss, /\.home-inspiration-panel/)
assert.match(pagesCss, /\.home-guide-card/)
assert.match(pagesCss, /\.home-theme-grid/)
assert.match(pagesCss, /\.home-province-grid/)
assert.match(pagesCss, /Admin shell: compact command-center polish/)

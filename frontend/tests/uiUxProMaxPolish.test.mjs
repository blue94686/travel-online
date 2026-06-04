import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const read = file => fs.readFileSync(path.resolve(file), 'utf8')

const pageShell = read('src/components/common/PageShell.jsx')
const navbar = read('src/components/common/Navbar.jsx')
const scenicCard = read('src/components/common/ScenicCard.jsx')
const destinations = read('src/pages/DestinationsPage.jsx')
const tripPlanning = read('src/pages/TripPlanningPage.jsx')
const tokens = read('src/styles/tokens.css')
const globalCss = read('src/styles/global.css')
const pagesCss = read('src/styles/pages.css')

assert.match(pageShell, /className="skip-link"/)
assert.match(pageShell, /id="main-content"/)
assert.match(pageShell, /tabIndex=\{-1\}/)

assert.match(navbar, /aria-label="主导航"/)
assert.match(navbar, /aria-current=\{isActive\(link\.path\) \? 'page' : undefined\}/)
assert.match(navbar, /aria-haspopup="menu"/)
assert.match(navbar, /aria-expanded=\{userMenuOpen\}/)
assert.match(navbar, /aria-label=\{mobileMenuOpen \? '关闭导航菜单' : '打开导航菜单'\}/)

assert.match(scenicCard, /aria-label=\{`\$\{favorite \? '取消收藏' : '收藏'\}\$\{scenic\.name\}`\}/)
assert.match(scenicCard, /aria-pressed=\{favorite\}/)

assert.match(destinations, /className="floating-tab-shell"/)
assert.match(destinations, /role="tablist" aria-label="目的地浏览方式"/)
assert.match(destinations, /className="collection-highlight"/)
assert.match(destinations, /className="theme-card destination-theme-card"/)
assert.doesNotMatch(destinations, /className="theme-card" onClick/)

assert.match(tripPlanning, /role="tablist" aria-label="行程规划工具"/)
assert.match(tripPlanning, /htmlFor="route-start"/)
assert.match(tripPlanning, /className="panel map-stage-panel"/)
assert.match(tripPlanning, /className="sr-only" htmlFor="weather-city"/)

assert.match(tokens, /--tap-target: 44px/)
assert.match(tokens, /--motion-base: 220ms/)
assert.match(globalCss, /:focus-visible/)
assert.match(globalCss, /prefers-reduced-motion: reduce/)
assert.match(globalCss, /\.skip-link/)
assert.match(globalCss, /\.sr-only/)
assert.match(pagesCss, /\.app-tab-nav/)
assert.match(pagesCss, /\.map-planning-layout/)
assert.match(pagesCss, /\.weather-search-form/)

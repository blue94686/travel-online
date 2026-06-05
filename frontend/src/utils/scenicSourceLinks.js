const isHttpUrl = (value) => {
  const text = String(value || '').trim()
  return text.startsWith('http://') || text.startsWith('https://')
}

export function getScenicSourceLinks(item = {}) {
  if (!item) return []

  const official = String(item.official_website || '').trim()
  const source = String(item.source_url || '').trim()
  const links = []

  if (isHttpUrl(official)) {
    links.push({
      label: '官方网站',
      text: '点击访问官方平台',
      url: official,
    })
  }

  if (isHttpUrl(source) && source !== official) {
    links.push({
      label: '资料来源',
      text: '查看公开来源/地图入口',
      url: source,
    })
  }

  return links
}

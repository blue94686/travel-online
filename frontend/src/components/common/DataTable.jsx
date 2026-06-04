import { useState } from 'react'
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'

export default function DataTable({ columns, rows, pageSize = 10, pagination = false }) {
  const [page, setPage] = useState(1)
  const [sortKey, setSortKey] = useState(null)
  const [sortDir, setSortDir] = useState('asc')

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  let sorted = [...rows]
  if (sortKey) {
    sorted.sort((a, b) => {
      const av = a[sortKey] ?? ''
      const bv = b[sortKey] ?? ''
      const cmp = typeof av === 'number' && typeof bv === 'number' ? av - bv : String(av).localeCompare(String(bv))
      return sortDir === 'asc' ? cmp : -cmp
    })
  }

  const usePagination = pagination && sorted.length > pageSize
  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize))
  const currentPage = Math.min(page, totalPages)
  const displayRows = usePagination ? sorted.slice((currentPage - 1) * pageSize, currentPage * pageSize) : sorted

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map(col => (
              <th key={col.key} onClick={col.sortable ? () => handleSort(col.key) : undefined} style={col.sortable ? { cursor: 'pointer', userSelect: 'none' } : {}}>
                {col.label}
                {col.sortable && sortKey === col.key && (sortDir === 'asc' ? ' ↑' : ' ↓')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {displayRows.map((row, index) => (
            <tr key={row.id || index}>
              {columns.map(col => <td key={col.key}>{col.render ? col.render(row) : row[col.key]}</td>)}
            </tr>
          ))}
          {displayRows.length === 0 && (
            <tr><td colSpan={columns.length} style={{ textAlign: 'center', padding: 24, color: 'var(--color-muted)' }}>暂无数据</td></tr>
          )}
        </tbody>
      </table>
      {usePagination && (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8, padding: '12px 0' }}>
          <button className="ghost-btn" disabled={currentPage <= 1} onClick={() => setPage(1)}><ChevronsLeft size={14} /></button>
          <button className="ghost-btn" disabled={currentPage <= 1} onClick={() => setPage(p => p - 1)}><ChevronLeft size={14} /></button>
          <span style={{ fontSize: 13, color: 'var(--color-muted)' }}>第 {currentPage} / {totalPages} 页</span>
          <button className="ghost-btn" disabled={currentPage >= totalPages} onClick={() => setPage(p => p + 1)}><ChevronRight size={14} /></button>
          <button className="ghost-btn" disabled={currentPage >= totalPages} onClick={() => setPage(totalPages)}><ChevronsRight size={14} /></button>
        </div>
      )}
    </div>
  )
}

import { useEffect, useState } from 'react'
import { api } from './api.js'

const pageSize = 10

export function usePage(path, filters, offset, version = 0) {
  const [state, setState] = useState({ loading: true })
  const query = new URLSearchParams(Object.entries(filters).filter(([, value]) => value !== ''))
  query.set('limit', pageSize)
  query.set('offset', offset)
  const url = path + '?' + query

  useEffect(() => {
    const controller = new AbortController()
    setState({ loading: true })
    api(url, { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setState({ data }) })
      .catch((error) => { if (!controller.signal.aborted) setState({ error: error.message }) })

    return () => controller.abort()
  }, [url, version])

  return state
}

export function Pagination({ page, onChange }) {
  return (
    <div className="pagination">
      <span>共 {page.total} 筆{page.items.length > 0 && ` · 第 ${page.offset + 1}–${page.offset + page.items.length} 筆`}</span>
      <div className="button-row">
        <button type="button" disabled={page.offset === 0} onClick={() => onChange(Math.max(0, page.offset - page.limit))}>上一頁</button>
        <button type="button" disabled={page.offset + page.limit >= page.total} onClick={() => onChange(page.offset + page.limit)}>下一頁</button>
      </div>
    </div>
  )
}

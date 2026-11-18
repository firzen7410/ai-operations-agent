import { useEffect, useState } from 'react'
import { api, formatTime } from '../api.js'
import { Pagination, usePage } from '../paging.jsx'

const statusNames = { pending: '待處理', completed: '已完成', cancelled: '已取消' }
const emptyFilters = { status: '', start: '', end: '' }

function OrderDetail({ id, onClose }) {
  const [state, setState] = useState({ loading: true })

  useEffect(() => {
    const controller = new AbortController()
    api(`/orders/${id}`, { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setState({ data }) })
      .catch((error) => { if (!controller.signal.aborted) setState({ error: error.message }) })

    return () => controller.abort()
  }, [id])

  return (
    <section className="panel order-detail">
      <div className="panel-heading"><h2>訂單 #{id} 明細</h2><button type="button" onClick={onClose}>關閉</button></div>
      {state.loading && <p role="status">載入明細中…</p>}
      {state.error && <p className="error" role="alert">{state.error}</p>}
      {state.data && (
        <div className="table-wrap">
          <table aria-label="訂單明細">
            <thead><tr><th>商品 ID</th><th>數量</th><th>成交單價</th></tr></thead>
            <tbody>
              {state.data.items.map((item) => (
                <tr key={item.id}><td>{item.product_id}</td><td>{item.quantity}</td><td>{item.unit_price}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export function OrdersPage() {
  const [inputs, setInputs] = useState(emptyFilters)
  const [filters, setFilters] = useState(emptyFilters)
  const [offset, setOffset] = useState(0)
  const [selected, setSelected] = useState(null)
  const [filterError, setFilterError] = useState('')
  const { loading, data, error } = usePage('/orders', filters, offset)

  function applyFilters(event) {
    event.preventDefault()
    if (inputs.start && inputs.end && inputs.start >= inputs.end) {
      setFilterError('起始日必須早於截止日。')
      return
    }

    setFilterError('')
    setOffset(0)
    setSelected(null)
    setFilters({
      status: inputs.status,
      start: inputs.start ? inputs.start + 'T00:00:00+08:00' : '',
      end: inputs.end ? inputs.end + 'T00:00:00+08:00' : '',
    })
  }

  return (
    <>
      <header className="page-heading"><h1>訂單查詢</h1><p>依狀態和日期篩選訂單，日期使用台灣時間。</p></header>
      <section className="panel data-panel">
        <form className="filter-form" onSubmit={applyFilters}>
          <label>狀態
            <select value={inputs.status} onChange={(event) => setInputs({ ...inputs, status: event.target.value })}>
              <option value="">全部</option>
              {Object.entries(statusNames).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <label>起始日<input type="date" value={inputs.start} onChange={(event) => setInputs({ ...inputs, start: event.target.value })} /></label>
          <label>截止日（不含）<input type="date" value={inputs.end} onChange={(event) => setInputs({ ...inputs, end: event.target.value })} /></label>
          <button className="primary">搜尋</button>
        </form>
        {loading && <p role="status">載入訂單中…</p>}
        {(filterError || error) && <p className="error" role="alert">{filterError || error}</p>}
        {data && (
          <>
            <div className="table-wrap">
              <table aria-label="訂單列表">
                <thead><tr><th>訂單編號</th><th>訂單時間</th><th>狀態</th><th>明細</th></tr></thead>
                <tbody>
                  {data.items.map((order) => (
                    <tr key={order.id}>
                      <td>#{order.id}</td><td>{formatTime(order.ordered_at)}</td>
                      <td><span className={`status ${order.status}`}>{statusNames[order.status]}</span></td>
                      <td><button type="button" className="text-button" onClick={() => setSelected(order.id)}>查看</button></td>
                    </tr>
                  ))}
                  {data.items.length === 0 && <tr><td colSpan="4">沒有符合條件的訂單。</td></tr>}
                </tbody>
              </table>
            </div>
            <Pagination page={data} onChange={(next) => { setOffset(next); setSelected(null) }} />
          </>
        )}
      </section>
      {selected !== null && <OrderDetail key={selected} id={selected} onClose={() => setSelected(null)} />}
    </>
  )
}

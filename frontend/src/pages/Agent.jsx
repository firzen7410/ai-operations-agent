import { useState } from 'react'
import { api, formatTime } from '../api.js'

const suggestions = [
  '找出庫存低於 10 件，且最近 30 天銷量超過 20 件的商品，並提供補貨建議。',
  '列出目前庫存低於 10 件的商品。',
  '彙總最近 30 天已完成訂單的銷量與銷售額。',
]

const toolNames = {
  get_low_stock_products: '低庫存商品',
  get_sales_summary: '銷售統計',
  calculate_restock: '補貨計算',
}

const runLabels = { running: '進行中', completed: '已完成', failed: '失敗' }

function RestockTable({ result }) {
  return (
    <section className="restock" aria-label="補貨建議">
      <h3>補貨建議</h3>
      <p className="muted">提前期 {result.lead_time_days} 天 · 安全庫存 {result.safety_stock} 件</p>
      {result.items.length === 0 ? <p>這一頁沒有符合條件的商品。</p> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>商品</th><th>庫存</th><th>銷量</th><th>建議量</th></tr></thead>
            <tbody>
              {result.items.map((item) => (
                <tr key={item.product_id}>
                  <td>{item.name}<small>{item.sku}</small></td>
                  <td>{item.stock}</td><td>{item.units_sold}</td>
                  <td><strong>{item.recommended_quantity}</strong></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {result.total > result.items.length && (
        <p className="muted">本次顯示 {result.items.length} 筆，共 {result.total} 筆。</p>
      )}
    </section>
  )
}

function RunDetails({ run, pending }) {
  return (
    <aside className="panel run-panel" aria-label="執行紀錄">
      <div className="panel-heading"><div><h2>執行紀錄</h2><p>檢視工具參數與資料來源</p></div></div>
      {pending && <p role="status" className="side-note">正在等待 Agent 回覆。</p>}
      {!pending && !run && <p className="side-note">送出問題後，這裡會顯示工具執行紀錄。</p>}
      {run && (
        <div className="run-content">
          <div className="run-meta">
            <span className={`status ${run.status}`}>{runLabels[run.status]}</span>
            <span>{formatTime(run.completed_at)}</span>
          </div>
          <p className="run-id">執行 ID <code>{run.id}</code></p>
          <ol className="tools">
            {run.tool_executions.map((step) => (
              <li key={step.id}>
                <details>
                  <summary>
                    <span>{Object.hasOwn(toolNames, step.tool_name) ? toolNames[step.tool_name] : step.tool_name}</span>
                    <span className={`status ${step.status}`}>{step.status === 'success' ? '成功' : '失敗'}</span>
                  </summary>
                  {step.error_message && <p className="error" role="status">{step.error_message}</p>}
                  {step.arguments && <><h3>參數</h3><pre>{JSON.stringify(step.arguments, null, 2)}</pre></>}
                  {step.result && <><h3>結果</h3><pre>{JSON.stringify(step.result, null, 2)}</pre></>}
                </details>
              </li>
            ))}
          </ol>
          {run.tool_executions.length === 0 && <p className="muted">這次執行沒有呼叫工具。</p>}
        </div>
      )}
    </aside>
  )
}

export function AgentPage() {
  const [message, setMessage] = useState('')
  const [turns, setTurns] = useState([])
  const [selected, setSelected] = useState(null)
  const busy = turns.some((turn) => turn.pending)
  const inspected = turns.find((turn) => turn.localId === selected)

  async function submit(event) {
    event.preventDefault()
    const question = message.trim()
    if (!question || busy) return

    const localId = turns.length
    setTurns((current) => [...current, { localId, question, pending: true }])
    setSelected(localId)
    setMessage('')
    try {
      const run = await api('/agent/runs', { method: 'POST', body: { message: question } })
      setTurns((current) => current.map((turn) =>
        turn.localId === localId ? { ...turn, pending: false, run } : turn
      ))
    } catch (error) {
      setTurns((current) => current.map((turn) =>
        turn.localId === localId ? { ...turn, pending: false, error: error.message } : turn
      ))
    }
  }

  return (
    <>
      <header className="page-heading"><h1>AI 營運助理</h1><p>查詢庫存、銷售趨勢與補貨建議。</p></header>
      <div className="agent-grid">
        <section className="panel chat" aria-label="對話">
          <div className="panel-heading"><div><h2>營運對話</h2><p>每次提問會建立一筆獨立的執行紀錄</p></div></div>
          <div className="chat-body" aria-live="polite">
            {turns.length === 0 && (
              <div className="empty-chat">
                <div className="chat-mark" aria-hidden="true">✦</div>
                <h3>今天想查詢什麼？</h3>
                <ul className="suggestions">
                  {suggestions.map((question) => (
                    <li key={question}><button type="button" onClick={() => setMessage(question)}>{question}</button></li>
                  ))}
                </ul>
              </div>
            )}
            {turns.map((turn) => (
              <article className="turn" key={turn.localId}>
                <p className="question">{turn.question}</p>
                <div className="answer">
                  {turn.pending && <p role="status">正在查詢與整理結果…</p>}
                  {turn.error && <p className="error" role="alert">{turn.error}</p>}
                  {turn.run?.error_message && <p className="error" role="alert">{turn.run.error_message}</p>}
                  {turn.run?.response && <p className="response">{turn.run.response}</p>}
                  {turn.run?.tool_executions
                    .filter((step) => step.tool_name === 'calculate_restock' && step.result)
                    .map((step) => <RestockTable key={step.id} result={step.result} />)}
                  {turn.run && (
                    <button type="button" className="text-button" onClick={() => setSelected(turn.localId)}>
                      查看此筆執行紀錄
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
          <form className="composer" onSubmit={submit}>
            <label htmlFor="agent-message">輸入營運問題</label>
            <textarea
              id="agent-message" rows="3" maxLength={2000} value={message}
              placeholder="例如，哪些商品需要補貨？"
              onChange={(event) => setMessage(event.target.value)}
            />
            <div className="composer-actions">
              <span className="muted">{message.length} / 2000</span>
              <button className="primary" disabled={busy || !message.trim()}>{busy ? '查詢中…' : '送出問題'}</button>
            </div>
          </form>
        </section>
        <RunDetails run={inspected?.run} pending={inspected?.pending} />
      </div>
    </>
  )
}

import { useState } from 'react'
import { api } from '../api.js'
import { Pagination, usePage } from '../paging.jsx'

const emptyFilters = { name: '', sku: '', stock_below: '' }
const emptyProduct = { sku: '', name: '', price: '', stock: '' }

function ProductEditor({ product, onSaved, onCancel }) {
  const [form, setForm] = useState(product ? {
    sku: product.sku,
    name: product.name,
    price: product.price,
    stock: product.stock,
  } : emptyProduct)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  function change(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
  }

  async function submit(event) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const saved = await api(product ? `/products/${product.id}` : '/products', {
        method: product ? 'PATCH' : 'POST',
        body: { ...form, stock: Number(form.stock) },
      })
      onSaved(saved)
    } catch (error) {
      setError(error.message)
      setBusy(false)
    }
  }

  return (
    <section className="panel editor" aria-label={product ? '編輯商品' : '新增商品'}>
      <h2>{product ? '編輯商品' : '新增商品'}</h2>
      <form onSubmit={submit} aria-busy={busy}>
        <div className="form-grid">
          <label>SKU<input name="sku" maxLength={64} value={form.sku} onChange={change} required /></label>
          <label>商品名稱<input name="name" maxLength={200} value={form.name} onChange={change} required /></label>
          <label>單價<input type="number" name="price" min="0" max="9999999.99" step="0.01" value={form.price} onChange={change} required /></label>
          <label>庫存<input type="number" name="stock" min="0" max="2147483647" step="1" value={form.stock} onChange={change} required /></label>
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="button-row">
          <button className="primary" disabled={busy}>{busy ? '儲存中…' : '儲存商品'}</button>
          <button type="button" onClick={onCancel} disabled={busy}>取消</button>
        </div>
      </form>
    </section>
  )
}

export function ProductsPage() {
  const [inputs, setInputs] = useState(emptyFilters)
  const [filters, setFilters] = useState(emptyFilters)
  const [offset, setOffset] = useState(0)
  const [version, setVersion] = useState(0)
  const [editor, setEditor] = useState(undefined)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const { data, loading, error: loadError } = usePage('/products', filters, offset, version)

  function applyFilters(event) {
    event.preventDefault()
    setOffset(0)
    setFilters({ ...inputs, name: inputs.name.trim(), sku: inputs.sku.trim() })
  }

  function refresh() {
    setEditor(undefined)
    setVersion((current) => current + 1)
  }

  function saveProduct(product) {
    setError('')
    setConfirmation(`已${editor ? '更新' : '新增'}商品 ${product.sku}（ID ${product.id}）。`)
    refresh()
  }

  async function remove(product) {
    if (!window.confirm(`確定刪除「${product.name}」？`)) return
    setDeleting(true)
    setError('')
    setConfirmation('')
    try {
      await api(`/products/${product.id}`, { method: 'DELETE' })
      if (data.items.length === 1 && offset > 0) setOffset(Math.max(0, offset - data.limit))
      refresh()
    } catch (error) {
      setError(error.message)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <>
      <header className="page-heading">
        <div><h1>商品管理</h1><p>查詢和維護商品、單價與庫存。</p></div>
        <button type="button" className="primary" onClick={() => setEditor(null)} disabled={editor !== undefined}>新增商品</button>
      </header>
      {editor !== undefined && (
        <ProductEditor product={editor} onSaved={saveProduct} onCancel={() => setEditor(undefined)} />
      )}
      <section className="panel data-panel">
        <form className="filter-form" onSubmit={applyFilters}>
          <label>商品名稱<input value={inputs.name} maxLength={200} onChange={(event) => setInputs({ ...inputs, name: event.target.value })} /></label>
          <label>SKU<input value={inputs.sku} maxLength={64} onChange={(event) => setInputs({ ...inputs, sku: event.target.value })} /></label>
          <label>庫存低於<input type="number" min="0" max="2147483647" value={inputs.stock_below} onChange={(event) => setInputs({ ...inputs, stock_below: event.target.value })} /></label>
          <button className="primary">搜尋</button>
        </form>
        {loading && <p role="status">載入商品中…</p>}
        {confirmation && <p role="status">{confirmation}</p>}
        {(error || loadError) && <p className="error" role="alert">{error || loadError}</p>}
        {data && (
          <>
            <div className="table-wrap">
              <table aria-label="商品列表">
                <thead><tr><th>商品名稱</th><th>SKU</th><th>單價</th><th>庫存</th><th>操作</th></tr></thead>
                <tbody>
                  {data.items.map((product) => (
                    <tr key={product.id}>
                      <td>{product.name}</td><td><code>{product.sku}</code></td>
                      <td>{product.price}</td><td>{product.stock}</td>
                      <td className="row-actions">
                        <button type="button" className="text-button" disabled={deleting || editor !== undefined} onClick={() => setEditor(product)}>編輯</button>
                        <button type="button" className="text-button danger" disabled={deleting || editor !== undefined} onClick={() => remove(product)}>刪除</button>
                      </td>
                    </tr>
                  ))}
                  {data.items.length === 0 && <tr><td colSpan="5">沒有符合條件的商品。</td></tr>}
                </tbody>
              </table>
            </div>
            <Pagination page={data} onChange={setOffset} />
          </>
        )}
      </section>
    </>
  )
}

import { StrictMode, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { AgentPage } from './pages/Agent.jsx'
import { ProductsPage } from './pages/Products.jsx'
import { OrdersPage } from './pages/Orders.jsx'
import './styles.css'

const views = [
  { id: 'agent', icon: '✦', label: 'AI 營運助理' },
  { id: 'products', icon: '▦', label: '商品管理' },
  { id: 'orders', icon: '≡', label: '訂單查詢' },
]

function App() {
  const [view, setView] = useState('agent')

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">✦</span>
          <div>AI Operations <small>Agent</small></div>
        </div>
        <nav aria-label="主要導覽">
          {views.map(({ id, icon, label }) => (
            <button
              key={id}
              type="button"
              aria-current={view === id ? 'page' : undefined}
              className={view === id ? 'nav-link active' : 'nav-link'}
              onClick={() => setView(id)}
            >
              <span aria-hidden="true">{icon}</span>{label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="workspace">
        <div hidden={view !== 'agent'}><AgentPage /></div>
        {view === 'products' && <ProductsPage />}
        {view === 'orders' && <OrdersPage />}
      </main>
    </div>
  )
}

createRoot(document.getElementById('root')).render(<StrictMode><App /></StrictMode>)

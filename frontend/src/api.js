export async function api(path, { method = 'GET', body, signal } = {}) {
  const response = await fetch('/api' + path, {
    method,
    signal,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (!response.ok) {
    const { detail } = await response.json().catch(() => ({}))
    const message = typeof detail === 'string' ? detail : detail?.[0]?.msg
    throw new Error(message || `API 請求失敗（HTTP ${response.status}）。`)
  }
  return response.status === 204 ? null : response.json()
}

export const dateTime = new Intl.DateTimeFormat('zh-TW', {
  dateStyle: 'medium',
  timeStyle: 'short',
  timeZone: 'Asia/Taipei',
})

export function formatTime(value) {
  return value ? dateTime.format(new Date(value)) : '—'
}

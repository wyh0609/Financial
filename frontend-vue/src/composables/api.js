// 自动检测当前访问地址，确保同源请求正确
const API_BASE = ''

export async function fetchConversations() {
  const resp = await fetch(`${API_BASE}/api/conversations`)
  return resp.json()
}

export async function createConversation(title = '新对话') {
  const resp = await fetch(`${API_BASE}/api/conversations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title })
  })
  return resp.json()
}

export async function fetchConversationMessages(conversationId) {
  const resp = await fetch(`${API_BASE}/api/conversations/${conversationId}`)
  return resp.json()
}

export async function deleteConversation(conversationId) {
  await fetch(`${API_BASE}/api/conversations/${conversationId}`, { method: 'DELETE' })
}

export async function uploadPdf(formData) {
  const resp = await fetch(`${API_BASE}/api/upload_pdf`, {
    method: 'POST',
    body: formData,
  })
  return resp.json()
}

export async function downloadAnalysisPdf(data) {
  const resp = await fetch(`${API_BASE}/api/download_analysis_pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!resp.ok) {
    const err = await resp.json()
    throw new Error(err.error || '未知错误')
  }
  const blob = await resp.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${data.company || '未知公司'}_${data.year || '未知年份'}_投资分析报告.pdf`
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}

export async function compareCompanies(companies, year) {
  const resp = await fetch(`${API_BASE}/api/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ companies, year })
  })
  return resp.json()
}

export async function careerAnalysis(companies, year) {
  const resp = await fetch(`${API_BASE}/api/career_analysis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ companies, year })
  })
  return resp.json()
}

export async function downloadCareerExcel(data) {
  const resp = await fetch(`${API_BASE}/api/download_career_excel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  if (!resp.ok) throw new Error('下载失败')
  const blob = await resp.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'career_analysis.xlsx'
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}

/**
 * 创建 SSE 流式连接（GET 方式，使用浏览器原生 EventSource）
 * EventSource 只支持 GET 请求，自动重连
 */
export function createSSEConnection(endpoint, params) {
  const query = new URLSearchParams(params).toString()
  const url = `${API_BASE}${endpoint}?${query}`
  console.log('[SSE] 连接:', url)
  const es = new EventSource(url)

  // 调试：监听所有事件
  es.addEventListener('message', (e) => {
    console.log('[SSE] raw message:', e.data?.substring(0, 100))
  })

  return es
}

/**
 * 使用 fetch + ReadableStream 实现流式 POST 请求
 * 比 EventSource 更灵活，支持 POST 和自定义 headers
 */
export function createFetchStream(endpoint, body) {
  const url = `${API_BASE}${endpoint}`
  console.log('[FetchStream] POST:', url)

  return fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(resp => {
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    return {
      async *parse() {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })

          // 按双换行分割 SSE 事件
          const lines = buffer.split('\n\n')
          buffer = lines.pop() || '' // 保留未完成的部分

          for (const line of lines) {
            if (!line.trim()) continue
            const match = line.match(/^data:\s*(.+)$/s)
            if (match) {
              try {
                yield JSON.parse(match[1].trim())
              } catch (e) {
                console.warn('[FetchStream] 解析失败:', e)
              }
            }
          }
        }

        // 处理剩余数据
        if (buffer.trim()) {
          const match = buffer.match(/^data:\s*(.+)$/s)
          if (match) {
            try {
              yield JSON.parse(match[1].trim())
            } catch (e) { /* ignore */ }
          }
        }
      },

      close() {
        reader.cancel().catch(() => {})
      }
    }
  })
}

export { API_BASE }

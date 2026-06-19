/**
 * API 基础地址 - 自动适配不同平台
 * H5: localhost
 * App/小程序: 局域网IP（需与电脑同一网络）
 */
function getBaseUrl() {
  // #ifdef H5
  return 'http://10.97.190.24:5000'
  // #endif
  // #ifndef H5
  // App/小程序环境：使用局域网IP，请改为你电脑的实际IP
  return 'http://10.97.190.24:5000'
  // #endif
}

export const BASE_URL = getBaseUrl()

/**
 * 通用请求封装
 */
function request(url, options = {}) {
  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + url,
      method: options.method || 'GET',
      data: options.data || {},
      header: {
        'Content-Type': 'application/json',
        ...options.header
      },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          reject(new Error(res.data?.error || `请求失败 (${res.statusCode})`))
        }
      },
      fail: (err) => {
        reject(new Error('网络连接失败，请检查网络或后端服务'))
      }
    })
  })
}

// ============ 对话管理 ============

export function fetchConversations() {
  return request('/api/conversations')
}

export function createConversation(title = '新对话') {
  return request('/api/conversations', {
    method: 'POST',
    data: { title }
  })
}

export function fetchConversationMessages(conversationId) {
  return request(`/api/conversations/${conversationId}`)
}

export function deleteConversation(conversationId) {
  return request(`/api/conversations/${conversationId}`, { method: 'DELETE' })
}

// ============ 文件上传 ============

export function uploadPdf(fileOrPath) {
  return new Promise((resolve, reject) => {
    console.log('[Upload API] 收到参数 type:', typeof fileOrPath,
      typeof fileOrPath === 'object' ? JSON.stringify(fileOrPath).substring(0, 120) : fileOrPath.substring(0, 80))

    // ===== H5: File/Blob 对象用 fetch + FormData =====
    const isFileBlob = (typeof Blob !== 'undefined' && fileOrPath instanceof Blob) ||
                        (typeof File !== 'undefined' && fileOrPath instanceof File)

    if (isFileBlob) {
      console.log('[Upload API] H5 File/Blob 上传:', fileOrPath.name, fileOrPath.size)
      const formData = new FormData()
      formData.append('file', fileOrPath, fileOrPath.name || 'file.pdf')
      fetch(`${BASE_URL}/api/upload_pdf`, {
        method: 'POST',
        body: formData,
      })
        .then(res => {
          if (!res.ok) throw new Error('HTTP ' + res.status)
          return res.json()
        })
        .then(resolve)
        .catch(() => reject(new Error('上传失败')))
      return
    }

    // ===== 字符串路径 / content URI / tempFiles 对象 → 统一用 uni.uploadFile =====
    let filePath = ''
    if (typeof fileOrPath === 'string') {
      filePath = fileOrPath
    } else if (typeof fileOrPath === 'object' && fileOrPath !== null) {
      filePath = fileOrPath.path || fileOrPath.tempFilePath || fileOrPath.uri || ''
    }

    if (!filePath) {
      reject(new Error('无效的文件'))
      return
    }

    console.log('[Upload API] uni.uploadFile 上传:', filePath.substring(0, 100))
    uni.uploadFile({
      url: `${BASE_URL}/api/upload_pdf`,
      filePath: filePath,
      name: 'file',
      success: (res) => {
        console.log('[Upload API] 响应:', res.statusCode, res.data?.substring(0, 120))
        if (res.statusCode === 200) {
          try { resolve(JSON.parse(res.data)) }
          catch { resolve(res.data) }
        } else {
          reject(new Error('上传失败 (' + res.statusCode + ')'))
        }
      },
      fail: (err) => {
        console.error('[Upload API] 失败:', JSON.stringify(err))
        reject(new Error('上传失败: ' + (err.errMsg || '')))
      }
    })
  })
}

// ============ 分析功能 ============

export function compareCompanies(companies, year) {
  return request('/api/compare_companies', {
    method: 'POST',
    data: { companies, year }
  })
}

export function careerAnalysis(companies, year) {
  return request('/api/career_analysis', {
    method: 'POST',
    data: { companies, year }
  })
}

// ============ SSE 流式连接 ============

/**
 * 创建 SSE 流式聊天连接
 * 使用 uni.request + enableChunked 实现流式响应
 */
export function createStreamChat(question, conversationId, onMessage, onError, onDone) {
  const taskId = Date.now().toString()

  // #ifdef H5
  // H5 环境使用原生 EventSource
  const params = new URLSearchParams({ question, conversation_id: conversationId || '' })
  const es = new EventSource(`${BASE_URL}/api/chat_stream_get?${params}`)

  es.onmessage = (event) => {
    try {
      const evt = JSON.parse(event.data)
      onMessage(evt)
      if (evt.type === 'done' || evt.type === 'error') {
        es.close()
        onDone(evt)
      }
    } catch (e) {
      console.warn('[SSE] 解析失败:', e)
    }
  }

  es.onerror = (err) => {
    console.error('[SSE] 连接错误:', err)
    es.close()
    onError(new Error('连接中断'))
  }

  return { close: () => es.close() }
  // #endif

  // #ifndef H5
  // 非 H5 环境（小程序/App）通过 POST 获取完整结果（后端已包含 thinking_steps）
  let aborted = false
  let retryCount = 0
  const maxRetries = 3

  async function poll() {
    if (aborted) return

    try {
      const res = await new Promise((resolve, reject) => {
        uni.request({
          url: `${BASE_URL}/api/chat`,
          method: 'POST',
          data: { question, conversation_id: conversationId || '' },
          timeout: 120000,
          success: (r) => resolve(r),
          fail: (e) => reject(e)
        })
      })

      if (res.statusCode === 200 && res.data) {
        const data = res.data

        // 先发送思考步骤
        if (data.thinking_steps && data.thinking_steps.length > 0) {
          for (const step of data.thinking_steps) {
            if (aborted) break
            onMessage({
              type: 'thinking_step',
              step: step.step || 0,
              label: step.label || '',
              status: step.status || '',
              content: step.content || ''
            })
            await new Promise(r => setTimeout(r, 200))
          }
        }

        // 发送元数据
        if (data.intent || data.entities || data.sources) {
          onMessage({
            type: 'meta',
            intent: data.intent,
            entities: data.entities,
            sources: data.sources,
            file: data.file,
          })
        }

        // 模拟流式效果：逐字显示
        if (data.answer) {
          let displayed = ''
          const chars = data.answer.split('')

          for (let i = 0; i < chars.length; i++) {
            if (aborted) break
            displayed += chars[i]
            onMessage({ type: 'chunk', content: chars[i] })
            await new Promise(r => setTimeout(r, 15))
          }

          onMessage({
            type: 'done',
            answer: data.answer,
            intent: data.intent,
            entities: data.entities,
            sources: data.sources,
            file: data.file,
          })
          onDone({ type: 'done' })
        } else if (data.error) {
          onMessage({ type: 'error', content: data.error })
          onDone({ type: 'error' })
        }
      } else {
        throw new Error('请求失败')
      }
    } catch (e) {
      console.error('[Poll] 错误:', e)
      retryCount++
      if (retryCount <= maxRetries && !aborted) {
        setTimeout(poll, 2000 * retryCount)
      } else {
        onError(e)
      }
    }
  }

  poll()

  return {
    close: () => { aborted = true }
  }
  // #endif
}

/**
 * 创建投资人分析流式连接（专用接口）
 */
export function createStreamInvestAnalysis(question, conversationId, onMessage, onError, onDone) {
  // #ifdef H5
  // H5 环境使用原生 EventSource 调用投资人分析接口
  const params = new URLSearchParams({
    question,
    conversation_id: conversationId || ''
  })
  const es = new EventSource(`${BASE_URL}/api/invest_analysis_stream_get?${params}`)

  es.onmessage = (event) => {
    try {
      const evt = JSON.parse(event.data)
      onMessage(evt)
      if (evt.type === 'done' || evt.type === 'error') {
        es.close()
        onDone(evt)
      }
    } catch (e) {
      console.warn('[SSE-Invest] 解析失败:', e)
    }
  }

  es.onerror = (err) => {
    console.error('[SSE-Invest] 连接错误:', err)
    es.close()
    onError(new Error('连接中断'))
  }

  return { close: () => es.close() }
  // #endif

  // #ifndef H5
  // 非 H5 环境：使用 POST 接口 + 打字机效果
  let aborted = false

  async function fetchInvest() {
    if (aborted) return

    try {
      const res = await new Promise((resolve, reject) => {
        uni.request({
          url: `${BASE_URL}/api/invest_analysis`,
          method: 'POST',
          data: { question, conversation_id: conversationId || '' },
          timeout: 180000,
          success: (r) => resolve(r),
          fail: (e) => reject(e)
        })
      })

      if (res.statusCode === 200 && res.data) {
        const data = res.data

        if (data.answer) {
          // 先显示思考步骤（如果有）
          if (data.thinking_steps) {
            for (const step of data.thinking_steps) {
              if (aborted) break
              onMessage({
                type: 'thinking_step',
                step: step.step || 0,
                label: step.label || '',
                status: step.status || '',
                content: step.content || ''
              })
              await new Promise(r => setTimeout(r, 300))
            }
          }

          // 显示元数据
          onMessage({
            type: 'meta',
            entities: data.entities || [],
            sources: data.sources || []
          })

          // 逐字输出答案
          let displayed = ''
          const chars = data.answer.split('')
          for (let i = 0; i < chars.length; i++) {
            if (aborted) break
            displayed += chars[i]
            onMessage({ type: 'chunk', content: chars[i] })
            await new Promise(r => setTimeout(r, 15))
          }

          // 完成
          onMessage({
            type: 'done',
            answer: data.answer,
            intent: data.intent || 'invest_analysis',
            entities: data.entities || [],
            sources: data.sources || [],
            file: data.file || null,
          })
          onDone({ type: 'done' })
        } else if (data.error) {
          onMessage({ type: 'error', content: data.error })
          onDone({ type: 'error' })
        }
      } else {
        throw new Error(`请求失败 (${res.statusCode})`)
      }
    } catch (e) {
      console.error('[Invest] 错误:', e)
      onError(e)
    }
  }

  fetchInvest()

  return {
    close: () => { aborted = true }
  }
  // #endif
}

// ============ PDF 下载 ============

/**
 * 下载分析报告 PDF
 * @param {Object} msg - 消息对象（包含 company, year, content 等信息）
 */
export function downloadAnalysisPDF(msg) {
  return new Promise((resolve, reject) => {
    const company = msg.company || ''
    const year = msg.year || ''
    const analysisText = msg.content || ''

    if (!company || !year || !analysisText) {
      uni.showToast({ title: '缺少分析数据', icon: 'none' })
      reject(new Error('缺少分析数据'))
      return
    }

    // #ifdef H5
    // H5：使用 fetch 下载
    uni.showLoading({ title: '生成报告中...' })
    fetch(`${BASE_URL}/api/download_analysis_pdf`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        company,
        year,
        analysis_text: analysisText
      })
    })
    .then(res => {
      if (!res.ok) throw new Error('生成失败')
      return res.blob()
    })
    .then(blob => {
      uni.hideLoading()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${company}_${year}_投资分析报告.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      resolve(true)
    })
    .catch(err => {
      uni.hideLoading()
      console.error('[Download] 失败:', err)
      uni.showToast({ title: '生成失败', icon: 'none' })
      reject(err)
    })
    return
    // #endif

    // #ifdef APP-PLUS
    // App端：先 POST 请求生成 PDF 并获取下载 token，再用 uni.downloadFile 下载
    const fileName = `${company}_${year}_投资分析报告.pdf`

    uni.showLoading({ title: '生成报告中...' })

    // 第一步：POST 请求生成 PDF，后端返回 { download_token: "xxx" }
    uni.request({
      url: `${BASE_URL}/api/generate_analysis_pdf`,
      method: 'POST',
      data: { company, year, analysis_text: analysisText },
      timeout: 60000,
      success: (res) => {
        if (res.statusCode !== 200 || !res.data || !res.data.download_token) {
          uni.hideLoading()
          const errMsg = res.data?.error || '生成失败'
          uni.showToast({ title: errMsg, icon: 'none' })
          reject(new Error(errMsg))
          return
        }

        // 第二步：用 uni.downloadFile 下载 PDF
        const downloadUrl = `${BASE_URL}/api/download_pdf_by_token?token=${res.data.download_token}`
        uni.downloadFile({
          url: downloadUrl,
          success: (downloadRes) => {
            uni.hideLoading()
            if (downloadRes.statusCode === 200) {
              uni.openDocument({
                filePath: downloadRes.tempFilePath,
                fileType: 'pdf',
                showMenu: true,
                success: function() { resolve(true) },
                fail: function(err) {
                  console.error('[Download] openDocument 失败:', err)
                  uni.showToast({ title: '已下载', icon: 'success' })
                  resolve(true)
                }
              })
            } else {
              uni.showToast({ title: '下载失败', icon: 'none' })
              reject(new Error('下载失败'))
            }
          },
          fail: (err) => {
            uni.hideLoading()
            console.error('[Download] downloadFile 失败:', err)
            uni.showToast({ title: '下载失败', icon: 'none' })
            reject(err)
          }
        })
      },
      fail: (err) => {
        uni.hideLoading()
        console.error('[Download] 生成请求失败:', err)
        uni.showToast({ title: '网络错误', icon: 'none' })
        reject(err)
      }
    })
    return
    // #endif

    // 其他环境
    uni.showToast({ title: '当前环境暂不支持下载', icon: 'none' })
    resolve(false)
  })
}

export default { BASE_URL }

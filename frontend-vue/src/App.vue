<template>
  <div id="app">
    <Sidebar
      :conversations="conversations"
      :currentConversationId="currentConversationId"
      @new-chat="createNewConversation"
      @switch-chat="switchConversation"
      @delete-chat="deleteConversation"
    />
    <div class="main-content">
      <div class="header">
        <span class="logo">💹</span>
        <h1>{{ currentConversationTitle }}</h1>
        <span class="subtitle">金融财报智能问答</span>
      </div>

      <ChatArea
        ref="chatAreaRef"
        :messages="messages"
        :loading="loading"
        @send-suggestion="sendSuggestion"
        @download-pdf="downloadAnalysisPDF"
      />

      <UploadArea
        :uploading="uploading"
        :uploadStatus="uploadStatus"
        :uploadProgress="uploadProgress"
        :loading="loading"
        @upload="handleFileUpload"
        @compare="openCompareModal"
        @career="openCareerModal"
      />

      <InputArea
        ref="inputAreaRef"
        :loading="loading"
        @send="sendMessage"
        @invest="sendInvestAnalysis"
      />
    </div>

    <CompareModal
      v-if="showCompareModal"
      :compareResult="compareResult"
      :compareLoading="compareLoading"
      :compareError="compareError"
      @close="closeCompareModal"
      @compare="doCompare"
    />

    <CareerModal
      v-if="showCareerModal"
      :careerResult="careerResult"
      :careerLoading="careerLoading"
      :careerError="careerError"
      @close="closeCareerModal"
      @analyze="doCareerAnalysis"
    />
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, reactive } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ChatArea from './components/ChatArea.vue'
import InputArea from './components/InputArea.vue'
import UploadArea from './components/UploadArea.vue'
import CompareModal from './components/CompareModal.vue'
import CareerModal from './components/CareerModal.vue'
import {
  fetchConversations, createConversation, fetchConversationMessages,
  deleteConversation as deleteConvApi, uploadPdf, downloadAnalysisPdf,
  compareCompanies, careerAnalysis, createSSEConnection
} from './composables/api.js'

const messages = ref([])
const loading = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref(null)
const chatAreaRef = ref(null)
const inputAreaRef = ref(null)

// 多对话
const conversations = ref([])
const currentConversationId = ref(null)

const currentConversationTitle = computed(() => {
  const conv = conversations.value.find(c => c.id === currentConversationId.value)
  return conv ? conv.title : '新对话'
})

// 公司对比
const showCompareModal = ref(false)
const compareLoading = ref(false)
const compareResult = ref(null)
const compareError = ref('')

// 职业分析
const showCareerModal = ref(false)
const careerLoading = ref(false)
const careerResult = ref(null)
const careerError = ref('')

function scrollToBottom() {
  nextTick(() => {
    const el = chatAreaRef.value?.$el || chatAreaRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

// 对话管理
async function loadConversations() {
  try {
    const data = await fetchConversations()
    if (data.conversations) conversations.value = data.conversations
  } catch (e) {
    console.error('加载对话列表失败:', e)
  }
}

async function createNewConversation() {
  try {
    const data = await createConversation()
    if (data.conversation_id) {
      await loadConversations()
      await switchConversation(data.conversation_id)
    }
  } catch (e) {
    console.error('创建对话失败:', e)
  }
}

async function switchConversation(id) {
  currentConversationId.value = id
  try {
    const data = await fetchConversationMessages(id)
    if (data.messages) {
      messages.value = data.messages.map(msg => ({
        role: msg.role,
        content: msg.content,
        thinking: msg.thinking || null,
        thinkingCollapsed: true,
        thinkingSteps: [],
        streaming: false,
        sources: msg.sources || [],
        isInvestAnalysis: msg.isInvestAnalysis || false,
        company: msg.company || '',
        year: msg.year || '',
      }))
    } else {
      messages.value = []
    }
  } catch (e) {
    console.error('加载对话消息失败:', e)
    messages.value = []
  }
  scrollToBottom()
}

async function deleteConversation(id) {
  if (!confirm('确定要删除这个对话吗？')) return
  try {
    await deleteConvApi(id)
    await loadConversations()
    if (currentConversationId.value === id) {
      currentConversationId.value = null
      messages.value = []
    }
  } catch (e) {
    console.error('删除对话失败:', e)
  }
}

// 发送消息
function sendSuggestion(text) {
  sendMessage(text)
}

async function sendMessage(questionText) {
  const question = questionText || inputAreaRef.value?.getText()?.trim()
  if (!question || loading.value) return

  if (!currentConversationId.value) {
    await createNewConversation()
  }

  // 添加用户消息
  messages.value.push({ role: 'user', content: question })
  inputAreaRef.value?.clearText()
  loading.value = true
  scrollToBottom()

  // 使用 reactive 确保深度响应式
  const botMsg = reactive({
    role: 'bot',
    content: '',
    streaming: true,
    sources: [],
    thinking: null,
    thinkingCollapsed: false,
    thinkingSteps: [],
  })
  messages.value.push(botMsg)
  scrollToBottom()

  console.log('[Chat] 发送问题:', question)

  try {
    const evtSource = createSSEConnection('/api/chat_stream_get', {
      question,
      conversation_id: currentConversationId.value || ''
    })

    evtSource.onmessage = function (event) {
      try {
        const evt = JSON.parse(event.data)
        console.log('[Chat] 收到事件:', evt.type, evt.content ? evt.content.substring(0, 50) : '')

        if (evt.type === 'thinking_step') {
          const idx = botMsg.thinkingSteps.findIndex(s => s.step === evt.step)
          if (idx >= 0) botMsg.thinkingSteps.splice(idx, 1, evt)
          else botMsg.thinkingSteps.push(evt)
          botMsg.thinkingCollapsed = false
          scrollToBottom()
        } else if (evt.type === 'meta') {
          botMsg.thinking = {
            intent: evt.intent, entities: evt.entities,
            file: evt.file, context: evt.context, is_open: evt.is_open,
          }
          botMsg.sources = evt.sources || []
        } else if (evt.type === 'chunk') {
          botMsg.content += evt.content
          scrollToBottom()
        } else if (evt.type === 'done') {
          botMsg.content = evt.answer || botMsg.content
          botMsg.streaming = false
          botMsg.sources = evt.sources || botMsg.sources
          if (!botMsg.thinking) {
            botMsg.thinking = {
              intent: evt.intent, entities: evt.entities,
              file: evt.file, context: evt.context, is_open: evt.is_open,
            }
          }
          evtSource.close()
          loading.value = false
          scrollToBottom()
          nextTick(() => inputAreaRef.value?.focus())
          console.log('[Chat] 流式完成')
        } else if (evt.type === 'error') {
          botMsg.content = '错误: ' + evt.content
          botMsg.streaming = false
          evtSource.close()
          loading.value = false
        }
      } catch (e) {
        console.warn('[Chat] 解析事件失败:', e, event.data)
      }
    }

    evtSource.onerror = function (err) {
      console.error('[Chat] SSE 连接错误:', err)
      botMsg.content = botMsg.content || '连接失败，请确认后端已启动'
      botMsg.streaming = false
      evtSource.close()
      loading.value = false
      scrollToBottom()
      nextTick(() => inputAreaRef.value?.focus())
    }
  } catch (e) {
    console.error('[Chat] 创建连接失败:', e)
    botMsg.content = '连接失败: ' + e.message
    botMsg.streaming = false
    loading.value = false
  }
}

// 投资人分析
async function sendInvestAnalysis() {
  const question = inputAreaRef.value?.getText()?.trim()
  if (!question || loading.value) return

  if (!currentConversationId.value) {
    await createNewConversation()
  }

  messages.value.push({ role: 'user', content: '📊 投资人分析: ' + question })
  inputAreaRef.value?.clearText()
  loading.value = true
  scrollToBottom()

  const botMsg = reactive({
    role: 'bot', content: '', streaming: true, sources: [],
    thinking: null, thinkingCollapsed: false, thinkingSteps: [],
    isInvestAnalysis: true, company: '', year: '',
  })
  messages.value.push(botMsg)
  scrollToBottom()

  console.log('[Chat] 发送投资分析:', question)

  try {
    const evtSource = createSSEConnection('/api/invest_analysis_stream_get', {
      question,
      conversation_id: currentConversationId.value || ''
    })

    evtSource.onmessage = function (event) {
      try {
        const evt = JSON.parse(event.data)
        if (evt.type === 'thinking_step') {
          const idx = botMsg.thinkingSteps.findIndex(s => s.step === evt.step)
          if (idx >= 0) botMsg.thinkingSteps.splice(idx, 1, evt)
          else botMsg.thinkingSteps.push(evt)
          botMsg.thinkingCollapsed = false
          scrollToBottom()
        } else if (evt.type === 'meta') {
          botMsg.sources = evt.sources || []
          if (evt.entities && evt.entities.length > 0) {
            botMsg.company = evt.entities[0] || ''
            for (const e of evt.entities) {
              const m = e.match(/(\d{4})/)
              if (m) { botMsg.year = m[1]; break }
            }
          }
        } else if (evt.type === 'chunk') {
          botMsg.content += evt.content
          scrollToBottom()
        } else if (evt.type === 'done') {
          botMsg.content = evt.answer || botMsg.content
          botMsg.streaming = false
          botMsg.sources = evt.sources || botMsg.sources
          if (evt.entities && evt.entities.length > 0) {
            botMsg.company = evt.entities[0] || botMsg.company
            for (const e of evt.entities) {
              const m = e.match(/(\d{4})/)
              if (m) { botMsg.year = m[1]; break }
            }
          }
          if (!botMsg.year) {
            const ym = question.match(/(\d{4})/)
            if (ym) botMsg.year = ym[1]
          }
          evtSource.close()
          loading.value = false
          scrollToBottom()
          nextTick(() => inputAreaRef.value?.focus())
        } else if (evt.type === 'error') {
          botMsg.content = '错误: ' + evt.content
          botMsg.streaming = false
          evtSource.close()
          loading.value = false
        }
      } catch (e) { console.warn('[Chat] 解析事件失败:', e) }
    }

    evtSource.onerror = function () {
      console.error('[Chat] SSE 连接错误')
      botMsg.content = botMsg.content || '连接失败，请确认后端已启动'
      botMsg.streaming = false
      evtSource.close()
      loading.value = false
      scrollToBottom()
      nextTick(() => inputAreaRef.value?.focus())
    }
  } catch (e) {
    console.error('[Chat] 创建连接失败:', e)
    botMsg.content = '连接失败: ' + e.message
    botMsg.streaming = false
    loading.value = false
  }
}

// PDF下载
async function downloadAnalysisPDF(msg) {
  if (!msg.content) { alert('缺少分析内容，无法生成PDF'); return }
  try {
    await downloadAnalysisPdf({
      company: msg.company || '未知公司',
      year: msg.year || '未知年份',
      analysis_text: msg.content,
    })
  } catch (e) {
    alert('下载失败: ' + e.message)
  }
}

// 文件上传
async function handleFileUpload(file) {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    uploadStatus.value = { type: 'error', message: '请选择PDF文件' }
    return
  }
  uploading.value = true
  uploadProgress.value = 0
  uploadStatus.value = { type: '', message: '正在上传...' }

  const formData = new FormData()
  formData.append('file', file)

  try {
    const data = await uploadPdf(formData)
    if (data.error) {
      uploadStatus.value = { type: 'error', message: '上传失败: ' + data.error }
    } else {
      uploadStatus.value = { type: 'success', message: '上传成功！已转换为: ' + data.txt_filename }
      messages.value.push({
        role: 'bot',
        content: '📄 PDF文件上传成功！\n文件名: ' + data.pdf_filename + '\n已转换为: ' + data.txt_filename + '\n\n现在可以提问关于该财报的问题了。'
      })
    }
  } catch (e) {
    uploadStatus.value = { type: 'error', message: '上传失败: ' + e.message }
  } finally {
    uploading.value = false
    uploadProgress.value = 0
    scrollToBottom()
  }
}

// 公司对比
function openCompareModal() {
  showCompareModal.value = true
  compareResult.value = null
  compareError.value = ''
}

function closeCompareModal() {
  showCompareModal.value = false
}

async function doCompare({ companies, year }) {
  compareLoading.value = true
  compareError.value = ''
  compareResult.value = null
  try {
    const data = await compareCompanies(companies, year)
    if (data.error) compareError.value = data.error
    else compareResult.value = data
  } catch (e) {
    compareError.value = '请求失败: ' + e.message
  } finally {
    compareLoading.value = false
  }
}

// 职业分析
function openCareerModal() {
  showCareerModal.value = true
  careerResult.value = null
  careerError.value = ''
}

function closeCareerModal() {
  showCareerModal.value = false
}

async function doCareerAnalysis({ companies, year }) {
  careerLoading.value = true
  careerError.value = ''
  careerResult.value = null
  try {
    const data = await careerAnalysis(companies, year)
    if (data.error) careerError.value = data.error
    else careerResult.value = data
  } catch (e) {
    careerError.value = '请求失败: ' + e.message
  } finally {
    careerLoading.value = false
  }
}

onMounted(() => {
  loadConversations()
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
  background: #f7f7f8;
  height: 100vh;
  overflow: hidden;
}

#app {
  width: 100%;
  height: 100vh;
  display: flex;
  background: #f7f7f8;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f7f7f8;
}

.header {
  background: transparent;
  color: #333;
  padding: 12px 24px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
  border-bottom: 1px solid rgba(0,0,0,0.05);
}

.header .logo {
  font-size: 20px;
  display: none;
}

.header h1 {
  font-size: 15px;
  font-weight: 600;
  color: #666;
}

.header .subtitle {
  font-size: 12px;
  color: #999;
  margin-left: auto;
}
</style>

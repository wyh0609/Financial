<template>
  <view class="page" :style="{ height: 'calc(100vh - ' + keyboardHeight + 'px)' }">
    <!-- 自定义导航栏 -->
    <view class="nav-bar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="nav-content">
        <view class="nav-left" @click="goConversations">
          <text class="icon-menu">☰</text>
        </view>
        <view class="nav-title">
          <text class="logo">💹</text>
          <text class="title">{{ currentTitle }}</text>
        </view>
        <view class="nav-right">
          <text class="nav-hint" v-if="!currentConversationId">新对话</text>
        </view>
      </view>
    </view>

    <!-- 聊天区域 -->
    <scroll-view
      class="chat-area"
      :style="{ paddingTop: (statusBarHeight + 60) + 'px' }"
      scroll-y
      :scroll-top="scrollTop"
      :scroll-with-animation="false"
      :scroll-into-view="scrollIntoViewId"
      :show-scrollbar="false"
    >
      <!-- 空状态 -->
      <view v-if="messages.length === 0" class="empty-state">
        <text class="empty-icon">📊</text>
        <text class="empty-title">ChatFinance</text>
        <text class="empty-subtitle">金融财报智能问答助手</text>
        
        <!-- 快捷问题 -->
        <view class="suggestions">
          <view
            class="suggestion-chip"
            v-for="(item, idx) in suggestions"
            :key="idx"
            @click="sendSuggestion(item)"
          >
            {{ item }}
          </view>
        </view>
      </view>

      <!-- 消息列表 -->
      <view
        v-for="(msg, idx) in messages"
        :key="idx"
        :id="'msg-' + idx"
        :class="['message-wrap', msg.role]"
      >
        <!-- 用户消息 -->
        <view v-if="msg.role === 'user'" class="message user">
          <view class="bubble user-bubble">{{ msg.content }}</view>
          <view class="avatar user-avatar" @click="showAvatarPicker">{{ userAvatar }}</view>
        </view>

        <!-- AI 消息 -->
        <view v-else class="message bot">
          <view class="avatar bot-avatar" @click="showAvatarPicker">{{ botAvatar }}</view>
          <view class="bot-content">
            <!-- 思考过程 -->
            <view v-if="showThinking(msg)" class="thinking-box">
              <view class="thinking-header" @click="toggleThinking(msg)">
                <text class="thinking-icon">🧠</text>
                <text class="thinking-title">思考过程</text>
                <text class="thinking-arrow">{{ msg.thinkingCollapsed ? '▼' : '▲' }}</text>
              </view>
              <view v-if="!msg.thinkingCollapsed" class="thinking-body">
                <!-- 思考步骤 - 只显示到当前进行中的步骤 -->
                <view
                  v-for="(step, si) in visibleSteps(msg)"
                  :key="si"
                  :class="['thinking-step', { 'step-done': step.status === 'done', 'step-loading': step.status === 'processing' }]"
                >
                  <view class="step-left">
                    <text class="step-status">
                      {{ step.status === 'done' ? '✓' : step.status === 'processing' ? '◉' : '○' }}
                    </text>
                    <text class="step-name">{{ getStepName(step) }}</text>
                  </view>
                  <text class="step-desc">{{ formatStepContent(step.content || step.description) }}</text>
                </view>
                <!-- 等待思考步骤到达时的占位 -->
                <view v-if="msg.streaming && (!msg.thinkingSteps || msg.thinkingSteps.length === 0)" class="thinking-step step-loading">
                  <view class="step-left">
                    <text class="step-status">◉</text>
                    <text class="step-name">正在启动思考引擎...</text>
                  </view>
                </view>
              </view>
            </view>

            <!-- 回答内容 -->
            <view v-if="msg.content" class="answer-box">
              <view class="answer-header">
                <text class="answer-label">📝 回答</text>
                <text v-if="msg.streaming" class="streaming-cursor">▌</text>
              </view>
              <rich-text class="answer-text" :nodes="renderMd(msg.content)" />
              
              <!-- 数据来源 -->
              <view v-if="msg.sources && msg.sources.length > 0" class="source-tags">
                <text class="source-label">📌 数据来源：</text>
                <text
                  v-for="(src, si) in msg.sources"
                  :key="si"
                  :class="['source-tag', src.includes('知识库') ? 'tag-kb' : 'tag-other']"
                >{{ src }}</text>
              </view>

              <!-- 投资分析下载按钮 -->
              <view v-if="msg.isInvestAnalysis && !msg.streaming" class="download-btn" @click="downloadPDF(msg)">
                📥 下载PDF报告
              </view>
            </view>

            <!-- 流式加载中 -->
            <view v-if="msg.streaming && !msg.content" class="typing-box">
              <view class="typing-dots">
                <view class="dot"></view>
                <view class="dot"></view>
                <view class="dot"></view>
              </view>
            </view>
          </view>
        </view>
      </view>

      <!-- 滚动到底部锚点 -->
      <view id="scroll-bottom-anchor" style="height: 1px; width: 1px;"></view>
    </scroll-view>

    <!-- 底部输入区（flex 子项，不使用 fixed，避免滑动时移位） -->
    <view class="input-area">
      <!-- 功能栏 -->
      <view class="toolbar">
        <view class="tool-btn" @click.stop="triggerFileInput">
          <text>📎</text>
          <text class="tool-text">上传</text>
        </view>
        <view class="tool-btn" @click="goCompare">
          <text>📊</text>
          <text class="tool-text">对比</text>
        </view>
        <view class="tool-btn" @click="goInvestAnalysis">
          <text>📈</text>
          <text class="tool-text">投资</text>
        </view>
        <view class="tool-btn" @click="goCareer">
          <text>💼</text>
          <text class="tool-text">职业</text>
        </view>
      </view>

      <!-- 输入框 -->
      <view class="input-row">
        <input
          class="input-field"
          type="text"
          v-model="inputText"
          placeholder="输入关于财报的问题..."
          :disabled="loading"
          confirm-type="send"
          @confirm="sendMessage"
          :adjust-position="false"
          @focus="onInputFocus"
          @blur="onInputBlur"
        />
        <view
          :class="['send-btn', { active: inputText.trim() && !loading }]"
          @click.stop="handleSend"
        >
          <text>{{ loading ? '...' : '发送' }}</text>
        </view>
      </view>
    </view>

  <!-- 头像选择弹窗 -->
  <view v-if="showAvatarModal" class="avatar-modal-mask" @click="showAvatarModal = false">
    <view class="avatar-modal" @click.stop>
      <text class="avatar-modal-title">选择头像</text>
      <view class="avatar-tabs">
        <text :class="['avatar-tab', { active: avatarTarget === 'user' }]" @click="avatarTarget = 'user'">我的头像</text>
        <text :class="['avatar-tab', { active: avatarTarget === 'bot' }]" @click="avatarTarget = 'bot'">AI头像</text>
      </view>
      <view class="avatar-grid">
        <view
          v-for="(emoji, ei) in avatarOptions"
          :key="ei"
          :class="['avatar-option', { selected: (avatarTarget === 'user' ? userAvatar : botAvatar) === emoji }]"
          @click="selectAvatar(emoji)"
        >{{ emoji }}</view>
      </view>
      <view class="avatar-modal-footer">
        <view class="avatar-btn cancel" @click="showAvatarModal = false">关闭</view>
      </view>
    </view>
  </view>
  </view>
</template>

<script setup>
import { ref, computed, nextTick, reactive } from 'vue'
import { onShow, onReady } from '@dcloudio/uni-app'
import {
  fetchConversations,
  createConversation,
  fetchConversationMessages,
  createStreamChat,
  createStreamInvestAnalysis,
  uploadPdf,
  downloadAnalysisPDF
} from '../../utils/api.js'
import { renderMarkdown as renderMd } from '../../utils/markdown.js'

// ============ 状态 ============
const messages = ref([])
const loading = ref(false)
const inputText = ref('')
const currentConversationId = ref(null)
const scrollToId = ref('')
const scrollTop = ref(0)
const scrollIntoViewId = ref('')
const statusBarHeight = ref(44)
const keyboardHeight = ref(0)
const safeAreaBottom = ref(0) // iOS 安全区域底部高度（刘海/底部横条）
const inputAreaHeight = ref(80) // 输入区域估算高度(px)，onReady 中实测

// 快捷建议
const suggestions = [
  '什么是净利润？',
  '2019年安记食品的营业利润率是多少？',
  '平潭发展2021年投资收益增长率',
]

// ============ 头像 ============
const AVATAR_KEY_USER = 'chatfinance_user_avatar'
const AVATAR_KEY_BOT = 'chatfinance_bot_avatar'

const userAvatar = ref('👤')
const botAvatar = ref('🤖')
const showAvatarModal = ref(false)
const avatarTarget = ref('user')

const avatarOptions = [
  '👤', '👨', '👩', '🧑', '👦', '👧', '🧒',
  '😊', '😎', '🤓', '🧐', '😄', '🥳', '🤩',
  '🦊', '🐱', '🐶', '🐼', '🐨', '🐰', '🐯',
  '🐸', '🐙', '🦄', '🐳', '🦁', '🐻', '🐧',
  '👽', '🤖', '🎃', '👻', '💀', '☠️', '👾',
  '💰', '📈', '💹', '🏦', '💎', '🎯', '⭐',
  '🔥', '💡', '🌟', '✨', '💪', '👍', '🎓',
]

function showAvatarPicker() {
  avatarTarget.value = 'user'
  showAvatarModal.value = true
}

function selectAvatar(emoji) {
  if (avatarTarget.value === 'user') {
    userAvatar.value = emoji
    uni.setStorageSync(AVATAR_KEY_USER, emoji)
  } else {
    botAvatar.value = emoji
    uni.setStorageSync(AVATAR_KEY_BOT, emoji)
  }
}

// 加载保存的头像
function loadAvatars() {
  const savedUser = uni.getStorageSync(AVATAR_KEY_USER)
  if (savedUser) userAvatar.value = savedUser
  const savedBot = uni.getStorageSync(AVATAR_KEY_BOT)
  if (savedBot) botAvatar.value = savedBot
}

// ============ 计算属性 ============
const currentTitle = computed(() => {
  // 有消息且正在流式输出 → 显示"对话中"
  if (messages.value.length > 0 && loading.value) return '对话中...'
  // 有 conversationId 且有消息 → 显示"聊天"
  if (messages.value.length > 0) return 'ChatFinance'
  // 默认
  return 'ChatFinance'
})

// ============ 生命周期 ============

onShow(async () => {
  // 检查是否从对话列表页切换过来
  const switchId = uni.getStorageSync('switchConversation')
  if (switchId !== undefined && switchId !== '') {
    // 清除标记
    uni.removeStorageSync('switchConversation')

    if (switchId) {
      // 切换到已有对话
      currentConversationId.value = switchId
      messages.value = [] // 先清空
      try {
        // 加载历史消息
        const data = await fetchConversationMessages(switchId)
        if (data.messages && data.messages.length > 0) {
          for (const msg of data.messages) {
            messages.value.push({
              role: msg.role,
              content: msg.content,
              streaming: false,
              sources: msg.sources || [],
              thinking: null,
              thinkingCollapsed: true,
              thinkingSteps: [],
            })
          }
        }
      } catch (e) {
        console.error('[Chat] 加载历史失败:', e)
        uni.showToast({ title: '加载失败', icon: 'none' })
      }
    } else {
      // 新建对话
      currentConversationId.value = null
      messages.value = []
    }
  }
})

onReady(() => {
  const sysInfo = uni.getSystemInfoSync()
  statusBarHeight.value = sysInfo.statusBarHeight || 44
  // iOS 安全区域底部（iPhone X 及以上有底部横条）
  if (sysInfo.safeAreaInsets) {
    safeAreaBottom.value = sysInfo.safeAreaInsets.bottom || 0
  } else if (sysInfo.safeArea) {
    // 兼容旧版本
    const screenHeight = sysInfo.screenHeight || sysInfo.windowHeight
    const safeBottom = sysInfo.safeArea.bottom || screenHeight
    safeAreaBottom.value = Math.max(0, screenHeight - safeBottom)
  }
  // 加载保存的头像
  loadAvatars()
  // 实测输入区高度
  nextTick(() => {
    const q = uni.createSelectorQuery()
    q.select('.input-area').boundingClientRect((r) => {
      if (r && r.height) inputAreaHeight.value = Math.ceil(r.height)
    }).exec()
  })

  // 监听键盘高度变化（最可靠的方式）
  uni.onKeyboardHeightChange((res) => {
    const h = res.height || 0
    if (h > 0) {
      keyboardHeight.value = h
    } else if (keyboardHeight.value > 0) {
      // 只在之前键盘打开时才重置（忽略初始和无效的0值）
      keyboardHeight.value = 0
    }
    // 延迟滚动：键盘弹起/收起有动画（~250ms），等布局稳定后再滚动
    setTimeout(() => {
      scrollBottom()
    }, 260)
  })

  // H5端：onKeyboardHeightChange 可能不触发，用 visualViewport 补充监听
  if (typeof window !== 'undefined' && window.visualViewport) {
    const onViewportResize = () => {
      const kbHeight = Math.max(0, window.innerHeight - window.visualViewport.height)
      if (kbHeight > 50) {
        keyboardHeight.value = kbHeight
      } else if (keyboardHeight.value > 0) {
        keyboardHeight.value = 0
      }
      setTimeout(() => scrollBottom(), 100)
    }
    window.visualViewport.addEventListener('resize', onViewportResize)
  }
})

// ============ 方法 ============

function showThinking(msg) {
  return (msg.thinkingSteps && msg.thinkingSteps.length > 0) ||
         msg.thinking ||
         msg.streaming
}

// 只显示到当前正在进行的步骤（不提前展示后续步骤）
function visibleSteps(msg) {
  if (!msg.thinkingSteps || msg.thinkingSteps.length === 0) return []
  const steps = msg.thinkingSteps
  // 找到最后一个 processing 或 done 的步骤索引
  let lastVisibleIdx = -1
  for (let i = 0; i < steps.length; i++) {
    if (steps[i].status === 'done' || steps[i].status === 'processing') {
      lastVisibleIdx = i
    }
  }
  // 如果没找到（步骤都还没开始），显示第一个
  if (lastVisibleIdx === -1 && steps.length > 0) lastVisibleIdx = 0
  return steps.slice(0, lastVisibleIdx + 1)
}

function toggleThinking(msg) {
  msg.thinkingCollapsed = !msg.thinkingCollapsed
}

// 处理发送按钮点击（兼容移动端）
function handleSend() {
  // 防止重复点击
  if (loading.value) return
  const text = inputText.value?.trim() || ''
  if (!text) {
    uni.showToast({ title: '请输入问题', icon: 'none' })
    return
  }
  sendMessage(text)
}

// 步骤名称映射（四字中文描述）
const STEP_NAMES = {
  // 通用步骤
  1: '意图识别',
  2: '实体提取',
  3: '知识检索',
  4: '数据查询',
  5: '逻辑推理',
  6: '结果生成',
  7: '答案整理',
  // 投资人分析专用
  'intent': '意图识别',
  'entity': '实体提取',
  'search': '知识检索',
  'query': '数据查询',
  'reason': '逻辑推理',
  'generate': '结果生成',
  'format': '格式化',
}

/**
 * 获取步骤的四字中文名称
 * 优先使用 step.label，其次使用 step.step 编号映射，最后用 "处理中"
 */
function getStepName(step) {
  // 如果有 label 字段，直接使用
  if (step.label && typeof step.label === 'string' && step.label.trim()) {
    const label = step.label.trim()
    // 如果已经是四字左右的中文名称，直接返回
    if (/^[\u4e00-\u9fa5]{2,6}$/.test(label)) {
      return label
    }
    // 否则截取前6个字符
    return label.substring(0, 6)
  }

  // 使用编号映射
  if (step.step !== undefined && step.step !== null) {
    return STEP_NAMES[step.step] || `第${step.step}步`
  }

  return '处理中'
}

/**
 * 格式化步骤描述内容
 * 将列表、对象等转为可读字符串
 */
function formatStepContent(content) {
  if (content === null || content === undefined || content === '') return ''
  if (Array.isArray(content)) {
    return content.map(item => {
      if (typeof item === 'object' && item !== null) return JSON.stringify(item)
      return String(item)
    }).join(', ')
  }
  if (typeof content === 'object') return JSON.stringify(content)
  return String(content)
}

let scrollThrottleTimer = null
function scrollBottom() {
  // 节流：50ms 内最多滚动一次，避免流式输出时频繁调用导致卡顿
  if (scrollThrottleTimer) return
  scrollThrottleTimer = setTimeout(() => {
    scrollThrottleTimer = null
    // 方式1：scroll-into-view 滚动到锚点（最可靠）
    scrollIntoViewId.value = ''
    nextTick(() => {
      scrollIntoViewId.value = 'scroll-bottom-anchor'
    })
    // 方式2：scroll-top 作为备选
    scrollTop.value = scrollTop.value > 999000 ? 999000 : 999999
  }, 50)
}

// 发送建议问题
function sendSuggestion(text) {
  sendMessage(text)
}

// 发送消息（主流程）
async function sendMessage(questionText) {
  // 优先使用传入参数，否则取输入框内容
  const question = (questionText || inputText.value || '').trim()
  if (!question || loading.value) return

  // 自动创建对话
  if (!currentConversationId.value) {
    try {
      const data = await createConversation('新对话')
      if (data.conversation_id) {
        currentConversationId.value = data.conversation_id
      }
    } catch (e) {
      console.error('[Chat] 创建对话失败:', e)
    }
  }

  // 添加用户消息
  messages.value.push({ role: 'user', content: question })
  inputText.value = ''
  loading.value = true
  scrollBottom()

  // 添加 AI 消息占位
  const botMsg = reactive({
    role: 'bot',
    content: '',
    streaming: true,
    sources: [],
    thinking: null,
    thinkingCollapsed: false,
    thinkingSteps: [],
    isInvestAnalysis: false,
  })
  messages.value.push(botMsg)
  scrollBottom()

  // 建立流式连接
  let closed = false
  
  createStreamChat(
    question,
    currentConversationId.value || '',
    
    // onMessage
    (evt) => {
      if (closed) return
      
      if (evt.type === 'thinking_step') {
        const idx = botMsg.thinkingSteps.findIndex(s => s.step === evt.step)
        if (idx >= 0) {
          botMsg.thinkingSteps.splice(idx, 1, evt)
        } else {
          botMsg.thinkingSteps.push(evt)
        }
        botMsg.thinkingCollapsed = false
        scrollBottom()
      } else if (evt.type === 'meta') {
        botMsg.thinking = {
          intent: evt.intent,
          entities: evt.entities,
          file: evt.file,
          context: evt.context,
        }
        botMsg.sources = evt.sources || []
      } else if (evt.type === 'chunk') {
        botMsg.content += evt.content
        scrollBottom()
      } else if (evt.type === 'done') {
        botMsg.content = evt.answer || botMsg.content
        botMsg.streaming = false
        botMsg.sources = evt.sources || botMsg.sources
        if (!botMsg.thinking) {
          botMsg.thinking = {
            intent: evt.intent,
            entities: evt.entities,
            file: evt.file,
            context: evt.context,
          }
        }
        loading.value = false
        closed = true
        scrollBottom()
      } else if (evt.type === 'error') {
        botMsg.content = '错误: ' + evt.content
        botMsg.streaming = false
        loading.value = false
        closed = true
        scrollBottom()
      }
    },
    
    // onError
    (err) => {
      if (closed) return
      botMsg.content = botMsg.content || '连接失败，请检查网络'
      botMsg.streaming = false
      loading.value = false
      closed = true
      scrollBottom()
    },
    
    // onDone
    () => {}
  )
}

// 投资人分析（流式 + 思考过程）- 使用专用接口
async function sendInvestAnalysis(question) {
  if (!question || loading.value) return

  if (!currentConversationId.value) {
    try {
      const data = await createConversation('新对话')
      if (data.conversation_id) {
        currentConversationId.value = data.conversation_id
      }
    } catch (e) {
      console.error('[Chat] 创建对话失败:', e)
    }
  }

  messages.value.push({ role: 'user', content: '📊 投资人分析: ' + question })
  inputText.value = ''
  loading.value = true
  scrollBottom()

  // 从问题中预提取公司/年份（用于下载PDF）
  const extractedCompany = question.split(/[,，\s]/)[0] || ''
  const yearMatch = question.match(/(\d{4})/)
  const extractedYear = yearMatch ? yearMatch[1] : ''

  // 添加 AI 消息占位（标记为投资人分析）
  const botMsg = reactive({
    role: 'bot',
    content: '',
    streaming: true,
    sources: [],
    thinking: null,
    thinkingCollapsed: false,
    thinkingSteps: [],
    isInvestAnalysis: true,
    company: extractedCompany,
    year: extractedYear,
  })
  messages.value.push(botMsg)
  scrollBottom()

  // 使用投资人分析专用流式接口
  let closed = false

  createStreamInvestAnalysis(
    question,
    currentConversationId.value || '',

    // onMessage - 处理各种事件类型
    (evt) => {
      if (closed) return

      if (evt.type === 'thinking_step') {
        // 思考步骤更新
        const idx = botMsg.thinkingSteps.findIndex(s => s.step === evt.step)
        if (idx >= 0) {
          botMsg.thinkingSteps.splice(idx, 1, evt)
        } else {
          botMsg.thinkingSteps.push(evt)
        }
        botMsg.thinkingCollapsed = false
        scrollBottom()
      } else if (evt.type === 'meta') {
        // 元数据：实体、来源等
        botMsg.sources = evt.sources || []
        // 提取公司和年份
        if (evt.entities && evt.entities.length > 0) {
          botMsg.company = evt.entities[0]
          for (const e of evt.entities) {
            const m = String(e).match(/(\d{4})/)
            if (m) { botMsg.year = m[1]; break }
          }
        }
      } else if (evt.type === 'chunk') {
        // 流式文本块
        botMsg.content += evt.content
        scrollBottom()
      } else if (evt.type === 'done') {
        // 完成
        botMsg.content = evt.answer || botMsg.content
        botMsg.streaming = false
        loading.value = false
        closed = true
        scrollBottom()
      } else if (evt.type === 'error') {
        botMsg.content = '错误: ' + evt.content
        botMsg.streaming = false
        loading.value = false
        closed = true
        scrollBottom()
      }
    },

    // onError
    (err) => {
      if (closed) return
      botMsg.content = botMsg.content || '连接失败，请检查网络'
      botMsg.streaming = false
      loading.value = false
      closed = true
      scrollBottom()
    },

    // onDone
    () => {}
  )
}

// ============ 文件上传 ============

/**
 * 触发文件选择 - 优先用官方 API，返回的临时路径直接传给 uni.uploadFile
 */
function triggerFileInput() {
  if (loading.value) return
  console.log('[Upload] 触发文件选择器...')

  // ===== 小程序: uni.chooseMessageFile =====
  if (typeof uni !== 'undefined' && uni.chooseMessageFile) {
    console.log('[Upload] 平台: 小程序 chooseMessageFile')
    uni.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['.pdf'],
      success: function(res) {
        if (res.tempFiles && res.tempFiles.length > 0) {
          doUploadPdf(res.tempFiles[0])
        }
      },
      fail: function() {
        uni.showToast({ title: '文件选择失败', icon: 'none' })
      }
    })
    return
  }

  // ===== H5: DOM input =====
  if (typeof document !== 'undefined' && document.createElement) {
    console.log('[Upload] 平台: H5 DOM input')
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.pdf'
    input.onchange = function(e) {
      const file = e.target.files && e.target.files[0]
      if (file) doUploadPdf(file)
    }
    document.body.appendChild(input)
    input.click()
    input.addEventListener('blur', function() {
      setTimeout(function() {
        if (document.body.contains(input)) document.body.removeChild(input)
      }, 200)
    })
    return
  }

  // ===== App Android: SAF Intent → content URI → 复制到临时目录 → uni.uploadFile =====
  if (typeof plus !== 'undefined' && plus.android) {
    console.log('[Upload] 平台: App Android')
    const REQUEST_CODE = 10001
    const main = plus.android.runtimeMainActivity()
    const Intent = plus.android.importClass('android.content.Intent')

    // 先检查是否有所有文件访问权限（Android 11+）
    const Build = plus.android.importClass('android.os.Build')
    const sdkInt = plus.android.invoke(Build.VERSION, 'SDK_INT')
    console.log('[Upload] Android SDK:', sdkInt)

    if (sdkInt >= 30) {
      // Android 11+: 检查 MANAGE_EXTERNAL_STORAGE 权限
      const Env = plus.android.importClass('android.os.Environment')
      const isManager = plus.android.invoke(Env, 'isExternalStorageManager')
      console.log('[Upload] isExternalStorageManager:', isManager)

      if (!isManager) {
        // 请求所有文件访问权限
        uni.showModal({
          title: '需要文件访问权限',
          content: '上传 PDF 文件需要"所有文件访问"权限，点击确定前往设置页面开启',
          confirmText: '去设置',
          cancelText: '取消',
          success: (res) => {
            if (res.confirm) {
              const Settings = plus.android.importClass('android.provider.Settings')
              const Uri = plus.android.importClass('android.net.Uri')
              const pkgName = main.getPackageName()
              const intent = new Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
              intent.setData(Uri.parse('package:' + pkgName))
              main.startActivity(intent)
            }
          }
        })
        return
      }
    }

    // 启动文件选择器 - 优先用系统 DocumentsUI（返回可读的 content URI）
    // 小米文件管理器的 myprovider 返回空流，必须避开
    const intent = new Intent(Intent.ACTION_OPEN_DOCUMENT)
    intent.addCategory(Intent.CATEGORY_OPENABLE)
    intent.setType('application/pdf')
    // 用 setPackage 强制指定 DocumentsUI 包名（不指定 class，让系统自己选 Activity）
    const pm = main.getPackageManager()
    let useDocumentsUI = false
    try {
      if (plus.android.invoke(pm, 'getPackageInfo', 'com.google.android.documentsui', 0)) {
        intent.setPackage('com.google.android.documentsui')
        useDocumentsUI = true
        console.log('[Upload] 使用 Google DocumentsUI')
      }
    } catch (e) { /* not installed */ }
    if (!useDocumentsUI) {
      try {
        if (plus.android.invoke(pm, 'getPackageInfo', 'com.android.documentsui', 0)) {
          intent.setPackage('com.android.documentsui')
          useDocumentsUI = true
          console.log('[Upload] 使用 AOSP DocumentsUI')
        }
      } catch (e) { /* not installed */ }
    }
    if (!useDocumentsUI) {
      console.log('[Upload] 未找到 DocumentsUI, 使用默认文件管理器')
    }

    main.onActivityResult = function(requestCode, resultCode, dataIntent) {
      if (requestCode !== REQUEST_CODE) return
      main.onActivityResult = null

      const Activity = plus.android.importClass('android.app.Activity')
      if (resultCode !== Activity.RESULT_OK || !dataIntent) {
        console.log('[Upload] 用户取消选择')
        return
      }

      const uri = dataIntent.getData()
      if (!uri) return
      const uriStr = uri.toString()
      console.log('[Upload] 获取到 URI:', uriStr)

      // 获取原始文件名
      let safFileName = null
      try {
        const cr = main.getContentResolver()
        const cursor = plus.android.invoke(cr, 'query', uri, null, null, null, null)
        if (cursor) {
          const moved = plus.android.invoke(cursor, 'moveToFirst')
          if (moved) {
            const colIndex = plus.android.invoke(cursor, 'getColumnIndex', '_display_name')
            if (colIndex !== undefined && colIndex !== null && Number(colIndex) >= 0) {
              safFileName = plus.android.invoke(cursor, 'getString', Number(colIndex))
            }
          }
          plus.android.invoke(cursor, 'close')
        }
      } catch (e) {
        console.warn('[Upload] 获取文件名失败:', e)
      }
      console.log('[Upload] SAF 原始文件名:', safFileName)

      uni.showLoading({ title: '上传中...', mask: true })

      // ===== 核心方案: 从 content URI 提取真实文件路径，用 plus.io 读取 =====
      // 参考 DCloud 官方社区方案 + Android DocumentsContract API

      const Uri = plus.android.importClass('android.net.Uri')
      const uriObj = Uri.parse(uriStr)
      let realFilePath = null

      try {
        const authority = '' + uriObj.getAuthority()
        const scheme = '' + uriObj.getScheme()
        console.log('[Upload] URI authority:', authority, 'scheme:', scheme)

        // 方案A: 通过 DocumentsContract 解析 media documents URI
        if (authority === 'com.android.providers.media.documents') {
          // content://com.android.providers.media.documents/document/document%3A1000072177
          // → document ID = "document:1000072177" → type=document, id=1000072177
          const DocumentsContract = plus.android.importClass('android.provider.DocumentsContract')
          const docId = '' + DocumentsContract.getDocumentId(uriObj)
          console.log('[Upload] documentId:', docId)
          const split = docId.split(':')
          const docType = split[0]
          const rowId = split[1]

          // 查询 MediaStore 获取 _data 列（真实文件路径）
          const MediaStoreFiles = plus.android.importClass('android.provider.MediaStore$Files')
          const cr = main.getContentResolver()
          const mediaUri = MediaStoreFiles.getContentUri('external')
          const cursor = plus.android.invoke(cr, 'query', mediaUri, null, '_id=?', [rowId], null)
          if (cursor) {
            const moved = plus.android.invoke(cursor, 'moveToFirst')
            if (moved) {
              const dataIdx = plus.android.invoke(cursor, 'getColumnIndex', '_data')
              if (dataIdx >= 0) {
                realFilePath = '' + plus.android.invoke(cursor, 'getString', dataIdx)
              }
            }
            plus.android.invoke(cursor, 'close')
          }
          console.log('[Upload] MediaStore _data:', realFilePath)
        }
        // 方案B: external storage documents
        else if (authority === 'com.android.externalstorage.documents') {
          const DocumentsContract = plus.android.importClass('android.provider.DocumentsContract')
          const docId = '' + DocumentsContract.getDocumentId(uriObj)
          const split = docId.split(':')
          if (split[0] === 'primary') {
            realFilePath = '/storage/emulated/0/' + split[1]
          }
          console.log('[Upload] external storage path:', realFilePath)
        }
        // 方案C: downloads documents
        else if (authority === 'com.android.providers.downloads.documents') {
          const DocumentsContract = plus.android.importClass('android.provider.DocumentsContract')
          const docId = '' + DocumentsContract.getDocumentId(uriObj)
          const ContentUris = plus.android.importClass('android.content.ContentUris')
          const dlUri = ContentUris.withAppendedId(
            Uri.parse('content://downloads/public_downloads'), docId)
          const cr = main.getContentResolver()
          const cursor = plus.android.invoke(cr, 'query', dlUri, null, null, null, null)
          if (cursor) {
            const moved = plus.android.invoke(cursor, 'moveToFirst')
            if (moved) {
              const dataIdx = plus.android.invoke(cursor, 'getColumnIndex', '_data')
              if (dataIdx >= 0) {
                realFilePath = '' + plus.android.invoke(cursor, 'getString', dataIdx)
              }
            }
            plus.android.invoke(cursor, 'close')
          }
          console.log('[Upload] downloads path:', realFilePath)
        }
        // 方案D: 通用 content:// URI - 直接查 _data
        else if (scheme === 'content') {
          const cr = main.getContentResolver()
          const cursor = plus.android.invoke(cr, 'query', uriObj, null, null, null, null)
          if (cursor) {
            const moved = plus.android.invoke(cursor, 'moveToFirst')
            if (moved) {
              const dataIdx = plus.android.invoke(cursor, 'getColumnIndex', '_data')
              if (dataIdx >= 0) {
                realFilePath = '' + plus.android.invoke(cursor, 'getString', dataIdx)
              }
            }
            plus.android.invoke(cursor, 'close')
          }
          console.log('[Upload] content query _data:', realFilePath)
        }
        // 方案E: file:// URI
        else if (scheme === 'file') {
          realFilePath = '' + uriObj.getPath()
          console.log('[Upload] file path:', realFilePath)
        }
      } catch (e) {
        console.warn('[Upload] 解析真实路径失败:', e)
      }

      // 防止 onerror 和 onloadend 同时触发导致重复调用
      let fallbackStarted = false
      function safeFallback(label) {
        if (fallbackStarted) return
        fallbackStarted = true
        console.log('[Upload] ' + label)
        copyAndUpload(uriStr, main, safFileName)
      }

      // 如果拿到了真实路径，用 plus.io 读取文件并 base64 上传
      if (realFilePath) {
        console.log('[Upload] 真实文件路径:', realFilePath)
        const fileUri = 'file://' + realFilePath
        plus.io.resolveLocalFileSystemURL(fileUri, (entry) => {
          console.log('[Upload] resolveLocalFileSystemURL 成功')
          entry.file((fileObj) => {
            console.log('[Upload] file 大小:', fileObj.size)
            if (fileObj.size === 0) {
              safeFallback('文件大小0，回退到 Java 复制方案')
              return
            }
            const reader = new plus.io.FileReader()
            reader.onloadend = (evt) => {
              const dataUrl = evt.target.result
              if (!dataUrl) {
                safeFallback('FileReader 结果为空，回退到 Java 复制方案')
                return
              }
              const b64 = dataUrl.split(',')[1]
              if (!b64) {
                safeFallback('FileReader base64为空，回退到 Java 复制方案')
                return
              }
              uploadBase64(b64, safFileName)
            }
            reader.onerror = () => {
              safeFallback('FileReader 失败，回退到 Java 复制方案')
            }
            reader.readAsDataURL(fileObj)
          }, () => {
            safeFallback('file 获取失败，回退到 Java 复制方案')
          })
        }, () => {
          safeFallback('resolveLocalFileSystemURL 失败，回退到 Java 复制方案')
        })
        return
      }

      // 没有真实路径，直接用 Java 复制方案
      copyAndUpload(uriStr, main, safFileName)
    }

    // Java 桥接复制 + base64 上传（回退方案）
    function copyAndUpload(uriStr, main, fileName) {
      console.log('[Upload] 使用 Java 复制方案...')
      let base64Result = null

      try {
        const Uri = plus.android.importClass('android.net.Uri')
        const cr = main.getContentResolver()
        const uriObj = Uri.parse(uriStr)

        // 策略1: ParcelFileDescriptor + FileInputStream + FileChannel (最可靠)
        let fileCopied = false
        let tempFilePath = null
        try {
          const File = plus.android.importClass('java.io.File')
          const FileInputStream = plus.android.importClass('java.io.FileInputStream')
          const FileOutputStream = plus.android.importClass('java.io.FileOutputStream')

          const extStorage = main.getExternalFilesDir(null)
          const extPath = '' + plus.android.invoke(extStorage, 'getAbsolutePath')
          const tempDir = extPath + '/uploads'
          const tempDirFile = new File(tempDir)
          if (!plus.android.invoke(tempDirFile, 'exists')) {
            plus.android.invoke(tempDirFile, 'mkdirs')
          }
          const tempName = 'upload_' + Date.now() + '.pdf'
          const tempFile = new File(tempDir + '/' + tempName)

          // 用 ParcelFileDescriptor 打开文件描述符
          const pfd = plus.android.invoke(cr, 'openFileDescriptor', uriObj, 'r')
          if (pfd) {
            const fd = plus.android.invoke(pfd, 'getFileDescriptor')
            const fis = new FileInputStream(fd)
            const fos = new FileOutputStream(tempFile)

            // 用 FileChannel.transferFrom
            const srcChannel = plus.android.invoke(fis, 'getChannel')
            const dstChannel = plus.android.invoke(fos, 'getChannel')
            if (srcChannel && dstChannel) {
              const srcSize = plus.android.invoke(srcChannel, 'size')
              console.log('[Upload] FileChannel source size:', srcSize)
              if (Number(srcSize) > 0) {
                const transferred = plus.android.invoke(dstChannel, 'transferFrom', srcChannel, 0, srcSize)
                console.log('[Upload] FileChannel transferred:', transferred)
              }
            }
            plus.android.invoke(dstChannel, 'close')
            plus.android.invoke(srcChannel, 'close')
            plus.android.invoke(fos, 'close')
            plus.android.invoke(fis, 'close')
            plus.android.invoke(pfd, 'close')

            const fileSize = plus.android.invoke(tempFile, 'length')
            console.log('[Upload] 临时文件大小:', fileSize)
            if (Number(fileSize) > 0) {
              fileCopied = true
              tempFilePath = '' + plus.android.invoke(tempFile, 'getAbsolutePath')
            }
          }
        } catch (e1) {
          console.warn('[Upload] ParcelFileDescriptor 方案失败:', e1.message || e1)
        }

        // 策略2: openInputStream + 逐字节读取 + ByteArrayOutputStream + Base64
        if (!fileCopied) {
          try {
            console.log('[Upload] 尝试逐字节读取方案...')
            const is = plus.android.invoke(cr, 'openInputStream', uriObj)
            if (is) {
              const available = plus.android.invoke(is, 'available')
              console.log('[Upload] inputStream.available():', available)

              const ByteArrayOutputStream = plus.android.importClass('java.io.ByteArrayOutputStream')
              const baos = new ByteArrayOutputStream()
              let totalRead = 0
              const startTime = Date.now()

              // 每次读一个字节，通过 JS-Java 桥接
              while (true) {
                const b = plus.android.invoke(is, 'read')
                if (b === -1 || b === null || b === undefined) break
                plus.android.invoke(baos, 'write', b)
                totalRead++
                // 每5万字打印进度
                if (totalRead % 50000 === 0) {
                  const elapsed = Date.now() - startTime
                  const speed = Math.round(totalRead / (elapsed / 1000))
                  console.log('[Upload] 进度:', totalRead, 'bytes, 速度:', speed, 'bytes/s')
                  // 更新加载提示
                  uni.showLoading({ title: '读取中 ' + Math.round(totalRead / 1024) + 'KB', mask: true })
                }
              }
              plus.android.invoke(is, 'close')
              const elapsed = Date.now() - startTime
              console.log('[Upload] 逐字节读取完成:', totalRead, 'bytes, 耗时:', elapsed, 'ms')

              if (totalRead > 0) {
                const Base64 = plus.android.importClass('android.util.Base64')
                const bytes = plus.android.invoke(baos, 'toByteArray')
                base64Result = '' + plus.android.invoke(Base64, 'encodeToString', bytes, 0)
                console.log('[Upload] Base64 编码长度:', base64Result.length)
              }
            }
          } catch (e2) {
            console.error('[Upload] 逐字节读取失败:', e2.message || e2)
          }
        }

        // 如果文件复制成功，用 plus.io 读取为 base64
        if (fileCopied && !base64Result) {
          const fileUri = 'file://' + tempFilePath
          console.log('[Upload] 文件复制成功，用 plus.io 读取:', fileUri)
          plus.io.resolveLocalFileSystemURL(fileUri, (entry) => {
            entry.file((fileObj) => {
              if (fileObj.size === 0) {
                uni.hideLoading()
                uni.showToast({ title: '文件为空', icon: 'none' })
                return
              }
              const reader = new plus.io.FileReader()
              reader.onloadend = (evt) => {
                const b64 = evt.target.result.split(',')[1]
                if (b64) {
                  uploadBase64(b64, fileName)
                } else {
                  uni.hideLoading()
                  uni.showToast({ title: '编码失败', icon: 'none' })
                }
              }
              reader.onerror = () => {
                uni.hideLoading()
                uni.showToast({ title: '读取失败', icon: 'none' })
              }
              reader.readAsDataURL(fileObj)
            }, () => {
              uni.hideLoading()
              uni.showToast({ title: '文件获取失败', icon: 'none' })
            })
          }, () => {
            uni.hideLoading()
            uni.showToast({ title: '文件解析失败', icon: 'none' })
          })
          return // 异步处理
        }
      } catch (e) {
        console.error('[Upload] Java 操作失败:', e)
      }

      // 如果已有 base64 结果，直接上传
      if (base64Result) {
        uploadBase64(base64Result, fileName)
        return
      }

      // 所有方案都失败
      uni.hideLoading()
      uni.showToast({ title: '文件读取失败，请尝试其他文件', icon: 'none', duration: 3000 })
    }

    // 上传 base64 到后端（防重复调用）
    let uploadDone = false
    function uploadBase64(base64Content, fileName) {
      if (uploadDone) {
        console.log('[Upload] 忽略重复上传请求')
        return
      }
      uploadDone = true
      console.log('[Upload] 上传 base64, 长度:', base64Content.length, '文件名:', fileName)
      uni.request({
        url: 'http://10.97.190.24:5000/api/upload_pdf_base64',
        method: 'POST',
        header: { 'Content-Type': 'application/json' },
        data: {
          filename: fileName || 'upload.pdf',
          content: base64Content
        },
        success: (res) => {
          uni.hideLoading()
          console.log('[Upload] 上传响应:', res.statusCode, JSON.stringify(res.data).substring(0, 200))
          if (res.statusCode === 200 && res.data && res.data.success) {
            uni.showToast({ title: '上传成功', icon: 'success' })
            messages.value.push({
              role: 'bot',
              content: '📄 PDF 上传成功！\n文件：' + (res.data.pdf_filename || '') + '\n现在可以提问关于该财报的问题了。',
              streaming: false,
            })
            scrollBottom()
          } else {
            uni.showToast({ title: (res.data && res.data.error) || '上传失败', icon: 'none' })
          }
        },
        fail: (err) => {
          uni.hideLoading()
          console.error('[Upload] 网络失败:', err)
          uni.showToast({ title: '网络错误', icon: 'none' })
        }
      })
    }

    main.startActivityForResult(intent, REQUEST_CODE)
    return
  }

  uni.showToast({ title: '当前环境不支持文件选择', icon: 'none' })
}

/**
 * 执行上传 - fileObj 支持: File对象(H5), 字符串路径/URI, tempFiles对象
 */
async function doUploadPdf(fileObj) {
  if (!fileObj) {
    uni.showToast({ title: '未选择文件', icon: 'none' })
    return
  }

  console.log('[Upload] 开始上传, 参数类型:', typeof fileObj,
    typeof fileObj === 'object' ? Object.keys(fileObj).join(',') : fileObj.substring(0, 80))
  uni.showLoading({ title: '上传解析中...', mask: true })

  try {
    const data = await uploadPdf(fileObj)
    console.log('[Upload] 上传响应:', data)
    uni.hideLoading()
    if (data && data.error) {
      uni.showToast({ title: data.error, icon: 'none' })
    } else {
      uni.showToast({ title: '上传成功', icon: 'success' })
      messages.value.push({
        role: 'bot',
        content: `📄 PDF 上传成功！\n文件：${data.pdf_filename || 'file.pdf'}\n已转换为：${data.txt_filename || 'file.txt'}\n\n现在可以提问关于该财报的问题了。`,
        streaming: false,
      })
      scrollBottom()
    }
  } catch (e) {
    uni.hideLoading()
    console.error('[Upload] 失败:', e)
    uni.showToast({ title: '上传失败，请重试', icon: 'none' })
  }
}

// 页面跳转
function goConversations() {
  uni.navigateTo({ url: '/pages/conversations/conversations' })
}

function goCompare() {
  uni.navigateTo({ url: '/pages/compare/compare' })
}

function goInvestAnalysis() {
  // 投资人分析：在当前对话中发送特殊标记
  const question = inputText.value?.trim() || ''
  if (question) {
    sendInvestAnalysis(question)
  } else {
    uni.showToast({ title: '请先输入公司名称和年份', icon: 'none' })
    // 聚焦输入框
    inputText.value = ''
  }
}

function goCareer() {
  uni.navigateTo({ url: '/pages/career/career' })
}

function downloadPDF(msg) {
  // 确保 company 和 year 不为空，尝试从内容中提取
  if (!msg.company || !msg.year) {
    const content = msg.content || ''
    // 尝试从分析内容中提取
    const companyMatch = content.match(/([^\s,，\n]{2,8})(?:公司|股份|集团|有限)/)
    if (companyMatch && !msg.company) msg.company = companyMatch[1]
    const yearMatch = content.match(/(\d{4})年?/)
    if (yearMatch && !msg.year) msg.year = yearMatch[1]
  }

  downloadAnalysisPDF(msg).then(() => {
    console.log('[Download] 下载完成')
  }).catch((err) => {
    console.error('[Download] 失败:', err)
  })
}

// 输入框焦点 - 不再手动处理键盘高度，由 onKeyboardHeightChange 统一处理
function onInputFocus(e) {
  // 仅在未获取到键盘高度时尝试使用事件高度
  if (keyboardHeight.value === 0 && e.detail && e.detail.height > 0) {
    keyboardHeight.value = e.detail.height
    setTimeout(() => scrollBottom(), 260)
  }
}

function onInputBlur() {
  // 不在这里重置 keyboardHeight，由 onKeyboardHeightChange 统一处理
  // 延迟滚动到底部，等待键盘收起动画完成
  setTimeout(() => {
    scrollBottom()
  }, 260)
}
</script>

<script>
export default {
  options: { styleIsolation: 'shared' }
}
</script>

<style lang="scss" scoped>
.page {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f7f7f8;
  /* iOS 平滑滚动 */
  -webkit-overflow-scrolling: touch;
  /* iOS 点击高亮禁用 */
  -webkit-tap-highlight-color: transparent;
}

/* 导航栏 */
.nav-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: linear-gradient(135deg, #4d6bfe 0%, #6b85ff 100%);
  
  .nav-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 88rpx;
    padding: 0 24rpx;
  }
  
  .nav-left {
    width: 64rpx;
    .icon-menu { font-size: 40rpx; color: #fff; }
  }
  
  .nav-title {
    display: flex;
    align-items: center;
    gap: 12rpx;
    .logo { font-size: 36rpx; }
    .title { font-size: 32rpx; font-weight: 600; color: #fff; }
  }
  
  .nav-right {
    width: 120rpx;
    text-align: right;
    .nav-hint { font-size: 24rpx; color: rgba(255,255,255,0.8); }
  }
}

/* 聊天区域 */
.chat-area {
  flex: 1;
  min-height: 0; /* flex 子项必须设置，否则不会缩小 */
  padding: 20rpx 24rpx;
  padding-top: calc(80rpx + env(safe-area-inset-top));
  /* iOS 平滑滚动 */
  -webkit-overflow-scrolling: touch;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 16rpx;
  
  .empty-icon { font-size: 96rpx; }
  .empty-title { font-size: 48rpx; font-weight: 700; color: #333; }
  .empty-subtitle { font-size: 28rpx; color: #888; margin-top: -12rpx; }
}

.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
  justify-content: center;
  margin-top: 32rpx;
  max-width: 100%;
  
  .suggestion-chip {
    padding: 18rpx 28rpx;
    background: #fff;
    border: 2rpx solid #e5e6eb;
    border-radius: 36rpx;
    font-size: 26rpx;
    color: #555;
    transition: all 0.2s;
    
    &:active {
      background: #4d6bfe;
      color: #fff;
      border-color: #4d6bfe;
    }
  }
}

/* 消息 */
.message-wrap {
  display: flex;
  margin-bottom: 24rpx;
  
  &.user { justify-content: flex-end; }
  &.bot { justify-content: flex-start; }
}

.message {
  display: flex;
  gap: 16rpx;
  max-width: 88%;
  
  &.user {
    flex-direction: row;
    
    .user-bubble {
      background: linear-gradient(135deg, #4d6bfe 0%, #6b85ff 100%);
      color: #fff;
      padding: 24rpx 32rpx;
      border-radius: 24rpx 4rpx 24rpx 24rpx;
      font-size: 30rpx;
      line-height: 1.6;
      word-break: break-word;
    }

    .user-avatar {
      width: 64rpx;
      height: 64rpx;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 30rpx;
      background: #fff;
      box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.08);
      flex-shrink: 0;
      margin-left: 12rpx;
      margin-right: 40rpx;
      margin-top: 10rpx;
    }
  }
  
  &.bot {
    .avatar {
      width: 64rpx;
      height: 64rpx;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 30rpx;
      background: #fff;
      box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.08);
      flex-shrink: 0;
    }
    
    .bot-content {
      flex: 1;
      min-width: 0;
    }
  }
}

/* 思考过程 */
.thinking-box {
  background: #f8f9ff;
  border-radius: 16rpx;
  margin-bottom: 16rpx;
  overflow: hidden;
  border: 2rpx solid #e8ecfd;
  
  .thinking-header {
    display: flex;
    align-items: center;
    gap: 10rpx;
    padding: 20rpx 24rpx;
    
    .thinking-icon { font-size: 28rpx; }
    .thinking-title { font-size: 26rpx; font-weight: 600; color: #4d6bfe; flex: 1; }
    .thinking-arrow { font-size: 22rpx; color: #999; }
  }
  
  .thinking-body {
    padding: 0 24rpx 20rpx;

    .thinking-step {
      padding: 16rpx 0;
      border-top: 2rpx dashed #e8ecfd;
      display: flex;
      flex-direction: column;
      gap: 8rpx;

      &:first-child { border-top: none; }

      &.step-done .step-name { color: #52c41a; }
      &.step-loading .step-name { color: #4d6bfe; }

      .step-left {
        display: flex;
        align-items: center;
        gap: 12rpx;

        .step-status {
          font-size: 26rpx;
          width: 36rpx;
          text-align: center;
          flex-shrink: 0;
        }

        .step-name {
          font-size: 26rpx;
          font-weight: 600;
          color: #4d6bfe;
          letter-spacing: 2rpx;
        }
      }

      .step-desc {
        font-size: 24rpx;
        color: #666;
        line-height: 1.5;
        padding-left: 48rpx;
      }
    }
  }
}

/* 回答框 */
.answer-box {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx 28rpx;
  box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.06);
  
  .answer-header {
    display: flex;
    align-items: center;
    gap: 8rpx;
    margin-bottom: 16rpx;
    
    .answer-label { font-size: 24rpx; font-weight: 600; color: #4d6bfe; }
    .streaming-cursor {
      color: #4d6bfe;
      animation: blink 0.8s infinite;
    }
  }
  
  .answer-text {
    font-size: 28rpx;
    line-height: 1.8;
    color: #333;
    word-break: break-word;
  }
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* 来源标签 */
.source-tags {
  margin-top: 20rpx;
  padding: 16rpx 20rpx;
  background: #f8f9ff;
  border-radius: 12rpx;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12rpx;
  
  .source-label { font-size: 22rpx; font-weight: 600; color: #666; }
  
  .source-tag {
    padding: 6rpx 16rpx;
    border-radius: 20rpx;
    font-size: 20rpx;
    font-weight: 500;
    
    &.tag-kb { background: #e6f4ea; color: #137333; }
    &.tag-other { background: #fef7e0; color: #b06000; }
  }
}

.download-btn {
  margin-top: 20rpx;
  padding: 18rpx 28rpx;
  background: #fff;
  color: #4d6bfe;
  border: 2rpx solid #4d6bfe;
  border-radius: 12rpx;
  text-align: center;
  font-size: 26rpx;
  
  &:active { background: #4d6bfe; color: #fff; }
}

/* 打字动画 */
.typing-box {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx 28rpx;
  box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.06);
  
  .typing-dots {
    display: flex;
    gap: 12rpx;
    
    .dot {
      width: 16rpx;
      height: 16rpx;
      border-radius: 50%;
      background: #4d6bfe;
      animation: bounce 1.4s infinite ease-in-out both;
      
      &:nth-child(1) { animation-delay: -0.32s; }
      &:nth-child(2) { animation-delay: -0.16s; }
    }
  }
}

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); }
  40% { transform: scale(1); }
}

/* 底部输入区 */
.input-area {
  flex-shrink: 0; /* 不被压缩，始终完整显示 */
  z-index: 99;
  background: #fff;
  box-shadow: 0 -2rpx 16rpx rgba(0,0,0,0.08);
  border-radius: 32rpx 32rpx 0 0;
  padding: 16rpx 24rpx;
  padding-bottom: calc(16rpx + env(safe-area-inset-bottom));
  
  .toolbar {
    display: flex;
    gap: 24rpx;
    padding: 8rpx 0 16rpx;
    
    .tool-btn {
      display: flex;
      align-items: center;
      gap: 8rpx;
      padding: 10rpx 20rpx;
      background: #f5f6fa;
      border-radius: 24rpx;
      
      text { font-size: 28rpx; }
      .tool-text { font-size: 22rpx; color: #666; }
      
      &:active { background: #e8e8ed; }
    }

    .tool-label {
      display: flex;
      align-items: center;
      gap: 8rpx;
      padding: 10rpx 20rpx;
      background: #f5f6fa;
      border-radius: 24rpx;
      cursor: pointer;

      text { font-size: 28rpx; }
      .tool-text { font-size: 22rpx; color: #666; }

      &:active { background: #e8e8ed; }
    }

    .hidden-input {
      position: absolute;
      width: 0;
      height: 0;
      opacity: 0;
      overflow: hidden;
    }
  }
  
  .input-row {
    display: flex;
    align-items: center;
    gap: 16rpx;
    
    .input-field {
      flex: 1;
      height: 80rpx;
      background: #f5f6fa;
      border-radius: 40rpx;
      padding: 0 32rpx;
      font-size: 28rpx;
      color: #333;
    }
    
    .send-btn {
      width: 144rpx;
      height: 80rpx;
      border-radius: 40rpx;
      background: #ccc;
      display: flex;
      align-items: center;
      justify-content: center;
      
      text { font-size: 28rpx; color: #fff; font-weight: 500; }
      
      &.active {
        background: linear-gradient(135deg, #4d6bfe 0%, #6b85ff 100%);
        
        &:active { opacity: 0.85; }
      }
    }
  }
}

/* 头像选择弹窗 */
.avatar-modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  z-index: 9999;
}

.avatar-modal {
  background: #fff;
  border-radius: 32rpx 32rpx 0 0;
  width: 100%;
  max-height: 70vh;
  padding: 32rpx;
  overflow-y: auto;

  .avatar-modal-title {
    font-size: 34rpx;
    font-weight: 700;
    color: #333;
    display: block;
    text-align: center;
    margin-bottom: 24rpx;
  }

  .avatar-tabs {
    display: flex;
    justify-content: center;
    gap: 40rpx;
    margin-bottom: 24rpx;

    .avatar-tab {
      font-size: 28rpx;
      color: #999;
      padding: 12rpx 32rpx;
      border-radius: 24rpx;

      &.active {
        color: #fff;
        background: #4d6bfe;
        font-weight: 600;
      }
    }
  }

  .avatar-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 20rpx;
    justify-content: center;

    .avatar-option {
      width: 80rpx;
      height: 80rpx;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 44rpx;
      border-radius: 50%;
      background: #f5f6fa;
      border: 4rpx solid transparent;

      &.selected {
        border-color: #4d6bfe;
        background: #eef0ff;
      }
    }
  }

  .avatar-modal-footer {
    margin-top: 32rpx;
    display: flex;
    justify-content: center;

    .avatar-btn {
      padding: 20rpx 80rpx;
      border-radius: 48rpx;
      font-size: 28rpx;
      font-weight: 600;

      &.cancel {
        background: #f5f6fa;
        color: #666;
      }
    }
  }
}
</style>

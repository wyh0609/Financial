<template>
  <div class="chat-area" ref="chatAreaEl">
    <div v-if="messages.length === 0" class="empty-state">
      <span class="icon">📊</span>
      <div class="empty-title">ChatFinance</div>
      <div class="empty-subtitle">向 ChatFinance 提问金融财报相关问题</div>
      <div class="suggestions">
        <span class="suggestion-chip" v-for="s in suggestions" :key="s" @click="$emit('send-suggestion', s)">{{ s }}</span>
      </div>
    </div>

    <MessageBubble
      v-for="(msg, idx) in messages"
      :key="idx"
      :msg="msg"
      @download-pdf="$emit('download-pdf', msg)"
    />

    <div v-if="loading" class="message bot">
      <div class="avatar">🤖</div>
      <div class="bubble">
        <div class="typing-dots">
          <span></span><span></span><span></span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import MessageBubble from './MessageBubble.vue'

defineProps({
  messages: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

defineEmits(['send-suggestion', 'download-pdf'])

const chatAreaEl = ref(null)
const suggestions = [
  '什么是净利润？',
  '2019年安记食品的营业利润率是多少？',
  '平潭发展2021年投资收益增长率',
  '研发费用对公司的竞争优势有何影响？',
]

defineExpose({ $el: chatAreaEl })
</script>

<style scoped>
.chat-area {
  flex: 1;
  overflow-y: scroll;
  overflow-x: hidden;
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  scrollbar-gutter: stable;
  align-items: center;
}

.chat-area::-webkit-scrollbar {
  width: 6px;
}

.chat-area::-webkit-scrollbar-thumb {
  background: #d0d5dd;
  border-radius: 3px;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #999;
  gap: 16px;
  min-height: 300px;
  max-width: 780px;
  width: 100%;
  padding: 40px 20px;
}

.empty-state .icon {
  font-size: 52px;
}

.empty-title {
  font-size: 32px;
  font-weight: 700;
  color: #333;
  letter-spacing: -1px;
}

.empty-subtitle {
  font-size: 15px;
  color: #888;
  margin-top: -4px;
}

.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 8px;
}

.suggestion-chip {
  padding: 8px 16px;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 20px;
  font-size: 13px;
  color: #555;
  cursor: pointer;
  transition: all 0.2s;
}

.suggestion-chip:hover {
  background: #4d6bfe;
  color: #fff;
  border-color: #4d6bfe;
}

.message.bot {
  display: flex;
  gap: 12px;
  animation: fadeIn 0.3s ease;
  min-width: 0;
  width: 100%;
  max-width: 780px;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  flex-shrink: 0;
  background: #fff;
  color: #4d6bfe;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

.bubble {
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.7;
  background: #fff;
  color: #333;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.typing-dots {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}

.typing-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4d6bfe;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-dots span:nth-child(1) { animation-delay: -0.32s; }
.typing-dots span:nth-child(2) { animation-delay: -0.16s; }
.typing-dots span:nth-child(3) { animation-delay: 0s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); }
  40% { transform: scale(1); }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>

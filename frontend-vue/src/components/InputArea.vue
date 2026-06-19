<template>
  <div class="input-area">
    <textarea v-model="input" placeholder="输入金融问题，按 Enter 发送..."
        @keydown.enter.exact.prevent="$emit('send')" :disabled="loading"
        rows="1" ref="inputBox"></textarea>
    <button @click="$emit('send')" :disabled="loading || !input.trim()">发送</button>
    <button @click="$emit('invest')" :disabled="loading || !input.trim()" class="invest-btn">📊 投资人分析</button>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  loading: { type: Boolean, default: false },
})

defineEmits(['send', 'invest'])

const input = ref('')
const inputBox = ref(null)

function getText() {
  return input.value
}

function clearText() {
  input.value = ''
}

function focus() {
  inputBox.value?.focus()
}

defineExpose({ getText, clearText, focus })
</script>

<style scoped>
.input-area {
  border-top: none;
  padding: 16px 24px 20px;
  display: flex;
  gap: 10px;
  flex-shrink: 0;
  background: transparent;
  justify-content: center;
}

.input-area textarea {
  flex: 1;
  max-width: 780px;
  border: 1.5px solid #e0e0e0;
  border-radius: 16px;
  padding: 12px 18px;
  font-size: 14px;
  font-family: inherit;
  resize: none;
  outline: none;
  max-height: 120px;
  line-height: 1.5;
  transition: all 0.2s ease;
  background: #fff;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

.input-area textarea:focus {
  border-color: #4d6bfe;
  box-shadow: 0 2px 16px rgba(77, 107, 254, 0.15);
}

.input-area button {
  background: #4d6bfe;
  color: #fff;
  border: none;
  border-radius: 14px;
  padding: 10px 22px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  box-shadow: 0 2px 8px rgba(77, 107, 254, 0.25);
}

.input-area button:hover:not(:disabled) {
  background: #3d5be0;
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(77, 107, 254, 0.35);
}

.input-area button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  transform: none !important;
  box-shadow: 0 1px 3px rgba(77, 107, 254, 0.12) !important;
}

.input-area button.invest-btn {
  background: linear-gradient(135deg, #a855f7, #7c3aed);
  box-shadow: 0 2px 8px rgba(168, 85, 247, 0.25);
}

.input-area button.invest-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #9333ea, #6d28d9);
  box-shadow: 0 4px 14px rgba(168, 85, 247, 0.35);
}
</style>

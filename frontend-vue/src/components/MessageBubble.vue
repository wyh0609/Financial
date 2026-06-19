<template>
  <div :class="['message', msg.role]">
    <div class="avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
    <div style="flex: 1; min-width: 0; overflow: hidden; width: 100%;">
      <!-- 思考过程 -->
      <ThinkingProcess
        v-if="(msg.thinkingSteps && msg.thinkingSteps.length > 0) || msg.thinking || msg.streaming"
        :msg="msg"
      />
      <!-- 最终答案 -->
      <div v-if="msg.content" class="answer-box">
        <div class="answer-label">📝 回答 <span v-if="msg.streaming" class="streaming-cursor">▌</span></div>
        <div class="markdown-body" v-html="renderMd(msg.content)"></div>
        <!-- 数据来源标签 -->
        <div v-if="msg.sources && msg.sources.length > 0" class="source-tags">
          <span class="source-tag-label">📌 数据来源：</span>
          <span v-for="(src, si) in msg.sources" :key="si"
                :class="['source-tag', src.includes('知识库') ? 'source-kb' : 'source-other']">
            {{ src }}
          </span>
        </div>
        <button v-if="msg.isInvestAnalysis" @click="$emit('download-pdf')" class="download-pdf-btn">
          📥 下载PDF报告
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import ThinkingProcess from './ThinkingProcess.vue'
import { renderMd } from '../utils/markdown.js'

defineProps({
  msg: { type: Object, required: true },
})

defineEmits(['download-pdf'])
</script>

<style scoped>
.message {
  display: flex;
  gap: 12px;
  animation: fadeIn 0.3s ease;
  min-width: 0;
  width: 100%;
  max-width: 780px;
}

.message.user {
  justify-content: flex-end;
  flex-direction: row-reverse;
}

.message.user .avatar {
  display: none;
}

.message.bot {
  justify-content: flex-start;
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
}

.message.bot .avatar {
  background: #fff;
  color: #4d6bfe;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

.answer-box {
  background: #fff;
  border: none;
  border-radius: 12px;
  padding: 16px 20px;
  font-size: 14px;
  line-height: 1.8;
  color: #333;
  word-break: break-word;
  overflow-wrap: break-word;
  max-width: 100%;
  box-sizing: border-box;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.streaming-cursor {
  color: #4d6bfe;
  animation: blink 0.8s infinite;
  font-weight: normal;
  margin-left: 2px;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.markdown-body {
  font-size: 14px;
  line-height: 1.8;
  color: #333;
}

.markdown-body :deep(h1) { font-size: 22px; font-weight: 700; margin: 16px 0 10px; color: #1a1a2e; border-bottom: 1px solid #eee; padding-bottom: 8px; }
.markdown-body :deep(h2) { font-size: 19px; font-weight: 600; margin: 14px 0 8px; color: #1a1a2e; }
.markdown-body :deep(h3) { font-size: 17px; font-weight: 600; margin: 12px 0 6px; color: #4d6bfe; }
.markdown-body :deep(h4) { font-size: 15px; font-weight: 600; margin: 10px 0 6px; color: #666; }
.markdown-body :deep(p) { margin: 6px 0; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { margin: 6px 0; padding-left: 20px; }
.markdown-body :deep(li) { margin: 3px 0; }
.markdown-body :deep(strong) { font-weight: 600; color: #1a1a2e; }
.markdown-body :deep(em) { font-style: italic; color: #666; }
.markdown-body :deep(code) { background: #f1f3f5; padding: 1px 5px; border-radius: 4px; font-size: 13px; font-family: 'Consolas', 'Monaco', monospace; }
.markdown-body :deep(pre) { background: #1e1e2e; color: #e0e0e0; border: none; border-radius: 8px; padding: 14px; overflow-x: auto; margin: 8px 0; }
.markdown-body :deep(pre code) { background: none; padding: 0; font-size: 13px; color: #e0e0e0; }
.markdown-body :deep(blockquote) { border-left: 3px solid #4d6bfe; margin: 8px 0; padding: 4px 12px; color: #666; background: #f8f9ff; border-radius: 0 6px 6px 0; }
.markdown-body :deep(table) { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 13px; }
.markdown-body :deep(th) { background: #f5f5f5; font-weight: 600; padding: 8px 10px; border: 1px solid #e0e0e0; text-align: left; }
.markdown-body :deep(td) { padding: 6px 10px; border: 1px solid #e0e0e0; }
.markdown-body :deep(tr:nth-child(even)) { background: #fafbfc; }
.markdown-body :deep(hr) { border: none; border-top: 1px solid #eee; margin: 12px 0; }

.answer-label {
  font-size: 12px;
  font-weight: 600;
  color: #4d6bfe;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.source-tags {
  margin-top: 12px;
  padding: 10px 14px;
  background: #f8f9ff;
  border-radius: 8px;
  border: 1px solid #e8ecfd;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  box-sizing: border-box;
}

.source-tag-label {
  font-size: 12px;
  font-weight: 600;
  color: #666;
}

.source-tag {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11.5px;
  font-weight: 500;
  white-space: nowrap;
  transition: all 0.2s ease;
}

.source-tag.source-kb {
  background: #e6f4ea;
  color: #137333;
  border: 1px solid #a8dab5;
}

.source-tag.source-other {
  background: #fef7e0;
  color: #b06000;
  border: 1px solid #fdd663;
}

.download-pdf-btn {
  margin-top: 12px;
  padding: 8px 16px;
  background: #fff;
  color: #4d6bfe;
  border: 1px solid #4d6bfe;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.download-pdf-btn:hover {
  background: #4d6bfe;
  color: #fff;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>

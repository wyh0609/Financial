<template>
  <div class="thinking-process">
    <div class="thinking-header" @click="msg.thinkingCollapsed = !msg.thinkingCollapsed">
      <span class="thinking-title">
        🧠 思考过程
        <span v-if="msg.streaming && (!msg.thinkingSteps || msg.thinkingSteps.length === 0)" class="thinking-live-dot"></span>
        <span v-else-if="msg.streaming && msg.thinkingSteps && msg.thinkingSteps.some(s => s.status === 'processing')" class="thinking-live-dot"></span>
      </span>
      <span class="thinking-toggle">{{ msg.thinkingCollapsed ? '展开' : '收缩' }}</span>
    </div>
    <div class="thinking-content" :class="{ collapsed: msg.thinkingCollapsed }">
      <!-- 逐步思考步骤 -->
      <template v-if="msg.thinkingSteps && msg.thinkingSteps.length > 0">
        <div v-for="(step, si) in msg.thinkingSteps" :key="'ts-'+si" class="step" :class="'step-' + step.status">
          <div class="step-icon">
            <template v-if="step.status === 'processing'">
              <span class="step-spinner"></span>
            </template>
            <template v-else-if="step.status === 'error'">✗</template>
            <template v-else>{{ step.step }}</template>
          </div>
          <div class="step-content">
            <span class="step-label">{{ step.label }}：</span>
            <template v-if="step.status === 'processing'">
              <span class="step-processing-text">正在处理...</span>
            </template>
            <template v-else-if="step.step === 2">
              {{ Array.isArray(step.content) ? step.content.join('、') || '无' : (step.content || '无') }}
            </template>
            <template v-else-if="step.step === 4">
              <div class="context-list">
                <div v-for="(ctx, ci) in (Array.isArray(step.content) ? step.content.slice(0, 10) : [])" :key="ci" class="context-item">
                  {{ ctx }}
                </div>
              </div>
            </template>
            <template v-else>
              {{ step.content || '' }}
            </template>
          </div>
        </div>
      </template>
      <!-- 等待思考步骤到达时的占位 -->
      <template v-else-if="msg.streaming && (!msg.thinkingSteps || msg.thinkingSteps.length === 0)">
        <div class="step step-processing">
          <div class="step-icon"><span class="step-spinner"></span></div>
          <div class="step-content">
            <span class="step-processing-text">正在启动思考引擎...</span>
          </div>
        </div>
      </template>
      <!-- 兼容旧格式 -->
      <template v-else-if="msg.thinking">
        <div class="step step-done">
          <div class="step-icon">1</div>
          <div class="step-content">
            <span class="step-label">意图识别：</span>
            {{ msg.thinking.intent }}
          </div>
        </div>
        <div v-if="!msg.thinking.is_open" class="step step-done">
          <div class="step-icon">2</div>
          <div class="step-content">
            <span class="step-label">实体提取：</span>
            {{ msg.thinking.entities.join('、') || '无' }}
          </div>
        </div>
        <div v-if="msg.thinking.file" class="step step-done">
          <div class="step-icon">3</div>
          <div class="step-content">
            <span class="step-label">匹配文件：</span>
            {{ msg.thinking.file }}
          </div>
        </div>
        <div v-if="msg.thinking.context && msg.thinking.context.length > 0" class="step step-done">
          <div class="step-icon">4</div>
          <div class="step-content">
            <span class="step-label">检索上下文：</span>
            <div class="context-list">
              <div v-for="(ctx, i) in msg.thinking.context.slice(0, 10)" :key="i" class="context-item">
                {{ ctx }}
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
defineProps({
  msg: { type: Object, required: true },
})
</script>

<style scoped>
.thinking-process {
  background: linear-gradient(135deg, #faf8ff 0%, #f0edff 50%, #e8f4ff 100%);
  border: 1px solid transparent;
  border-radius: 12px;
  padding: 14px 18px;
  margin-bottom: 10px;
  font-size: 13px;
  color: #5f6368;
  word-break: break-word;
  overflow-wrap: break-word;
  max-width: 100%;
  box-sizing: border-box;
  position: relative;
}

.thinking-process::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 12px;
  padding: 1.5px;
  background: linear-gradient(135deg, #4d6bfe, #a855f7, #4d6bfe);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}

.thinking-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  cursor: pointer;
  user-select: none;
}

.thinking-header:hover {
  opacity: 0.85;
}

.thinking-title {
  font-weight: 600;
  color: #4d6bfe;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13.5px;
}

.thinking-toggle {
  font-size: 12px;
  color: #888;
  padding: 3px 10px;
  border-radius: 12px;
  background: rgba(255,255,255,0.7);
  transition: all 0.2s;
  border: 1px solid rgba(0,0,0,0.06);
}

.thinking-toggle:hover {
  background: rgba(255,255,255,0.95);
  color: #555;
}

.thinking-content {
  transition: max-height 0.35s ease, opacity 0.3s ease;
  overflow: hidden;
}

.thinking-content.collapsed {
  max-height: 0 !important;
  opacity: 0;
  margin: 0;
}

.step {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 8px;
  padding: 4px 0;
}

.step:last-child {
  margin-bottom: 0;
}

.step-icon {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4d6bfe, #7c5cfc);
  color: #fff;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
}

.step-content {
  flex: 1;
  line-height: 1.6;
}

.step-label {
  font-weight: 600;
  color: #4d6bfe;
}

.context-list {
  margin-top: 4px;
  padding-left: 16px;
}

.context-item {
  margin-bottom: 2px;
  color: #777;
}

.thinking-live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4d6bfe, #a855f7);
  display: inline-block;
  animation: pulse-dot 1.2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.8); }
}

.step-processing {
  opacity: 0.7;
}

.step-done {
  opacity: 1;
  animation: stepFadeIn 0.3s ease;
}

@keyframes stepFadeIn {
  from { opacity: 0; transform: translateX(-6px); }
  to { opacity: 1; transform: translateX(0); }
}

.step-error .step-icon {
  background: linear-gradient(135deg, #d93025, #ff6b6b);
}

.step-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.step-processing-text {
  color: #999;
  font-style: italic;
  animation: processingPulse 1.5s ease-in-out infinite;
}

@keyframes processingPulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}
</style>

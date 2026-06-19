<template>
  <div class="upload-area">
    <label class="upload-btn" :class="{ disabled: uploading }">
      <span>📄</span>
      <span>{{ uploading ? '上传中...' : '上传PDF财报' }}</span>
      <input type="file" accept=".pdf" @change="onFileChange" :disabled="uploading">
    </label>
    <button @click="$emit('compare')" :disabled="loading || uploading" class="toolbar-action-btn compare-btn">📈 公司对比</button>
    <button @click="$emit('career')" :disabled="loading || uploading" class="toolbar-action-btn career-btn">💼 职业分析</button>
    <div v-if="uploadStatus" class="upload-status" :class="uploadStatus.type">
      {{ uploadStatus.message }}
    </div>
    <div v-if="uploadProgress > 0 && uploadProgress < 100" class="upload-progress">
      <div class="upload-progress-bar" :style="{ width: uploadProgress + '%' }"></div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  uploading: { type: Boolean, default: false },
  uploadStatus: { type: Object, default: null },
  uploadProgress: { type: Number, default: 0 },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['upload', 'compare', 'career'])

function onFileChange(event) {
  const file = event.target.files[0]
  if (file) {
    emit('upload', file)
    event.target.value = ''
  }
}
</script>

<style scoped>
.upload-area {
  padding: 8px 24px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  justify-content: center;
}

.upload-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  font-size: 13px;
  color: #555;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-btn:hover {
  border-color: #4d6bfe;
  color: #4d6bfe;
}

.upload-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.upload-btn input[type="file"] {
  display: none;
}

.toolbar-action-btn {
  padding: 8px 16px;
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fff;
  color: #555;
}

.toolbar-action-btn:hover:not(:disabled) {
  border-color: #4d6bfe;
  color: #4d6bfe;
}

.toolbar-action-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.upload-status {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 6px;
}

.upload-status.success {
  color: #137333;
  background: #e6f4ea;
}

.upload-status.error {
  color: #d93025;
  background: #fce8e6;
}

.upload-progress {
  width: 120px;
  height: 4px;
  background: #e0e0e0;
  border-radius: 2px;
  overflow: hidden;
}

.upload-progress-bar {
  height: 100%;
  background: #4d6bfe;
  border-radius: 2px;
  transition: width 0.3s;
}
</style>

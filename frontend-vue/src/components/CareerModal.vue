<template>
  <div class="career-modal-overlay" @click.self="$emit('close')">
    <div class="career-modal" style="position: relative;">
      <button class="career-close-btn" @click="$emit('close')">&times;</button>
      <h2>💼 职业性格分析</h2>

      <div class="career-input-area">
        <input v-model="companyInput" placeholder="输入公司名称，按回车添加"
            @keydown.enter.prevent="addCompany">
        <input v-model="yearInput" placeholder="年份（可选）" style="width: 150px;">
        <button @click="doAnalyze" :disabled="companies.length === 0 || careerLoading">
          {{ careerLoading ? '分析中...' : '开始分析' }}
        </button>
      </div>

      <div class="company-tags">
        <span v-for="(c, idx) in companies" :key="idx" class="company-tag">
          {{ c }}
          <button @click="removeCompany(idx)">&times;</button>
        </span>
      </div>

      <div v-if="careerError" style="color: #d93025; margin-bottom: 12px;">{{ careerError }}</div>

      <div v-if="careerResult">
        <div class="chart-container">
          <h3>人格类型得分对比</h3>
          <canvas ref="barCanvas"></canvas>
        </div>

        <div v-if="careerResult.analysis" class="analysis-content">
          <div class="markdown-body" v-html="renderCareerAnalysis()"></div>
        </div>

        <button @click="downloadExcel" class="download-excel-btn">📥 下载Excel报告</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import { renderMd, getScoreColor } from '../utils/markdown.js'
import { downloadCareerExcel } from '../composables/api.js'

const props = defineProps({
  careerResult: { type: Object, default: null },
  careerLoading: { type: Boolean, default: false },
  careerError: { type: String, default: '' },
})

const emit = defineEmits(['close', 'analyze'])

const companyInput = ref('')
const yearInput = ref('')
const companies = ref([])
const barCanvas = ref(null)

function addCompany() {
  const name = companyInput.value.trim()
  if (name && !companies.value.includes(name)) {
    companies.value.push(name)
  }
  companyInput.value = ''
}

function removeCompany(idx) {
  companies.value.splice(idx, 1)
}

function doAnalyze() {
  emit('analyze', { companies: [...companies.value], year: yearInput.value })
}

function renderCareerAnalysis() {
  if (!props.careerResult || !props.careerResult.analysis) return ''
  return renderMd(props.careerResult.analysis)
}

async function downloadExcel() {
  if (!props.careerResult) return
  try {
    await downloadCareerExcel({
      companies: props.careerResult.companies,
      personality_scores: props.careerResult.personality_scores,
    })
  } catch (e) {
    alert('下载Excel失败: ' + e.message)
  }
}

function drawCareerBarChart(data) {
  const canvas = barCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const dpr = window.devicePixelRatio || 1
  const container = canvas.parentElement
  const containerW = container ? container.clientWidth - 32 : 700
  const w = Math.min(containerW, 800)
  const h = Math.round(w * 0.52)
  canvas.width = w * dpr
  canvas.height = h * dpr
  canvas.style.width = w + 'px'
  canvas.style.height = h + 'px'
  ctx.scale(dpr, dpr)

  const padding = { top: 30, right: 100, bottom: 60, left: 45 }
  const chartW = w - padding.left - padding.right
  const chartH = h - padding.top - padding.bottom
  ctx.clearRect(0, 0, w, h)

  const personalities = ['ISTJ','ISFJ','INFJ','INTJ','ISTP','ISFP','INFP','INTP','ESTP','ESFP','ENFP','ENTP','ESTJ','ESFJ','ENFJ','ENTJ']
  const personalityScores = data.personality_scores || {}
  const companiesList = data.companies || []
  const colors = [[26,115,232],[227,116,0],[24,128,56],[217,48,37],[147,52,230],[0,151,167]]

  for (let i = 0; i <= 5; i++) {
    const y = padding.top + chartH - (i / 5) * chartH
    ctx.beginPath()
    ctx.strokeStyle = i === 0 ? '#bdc1c6' : '#e8eaed'
    ctx.lineWidth = i === 0 ? 1.2 : 0.6
    ctx.moveTo(padding.left, y)
    ctx.lineTo(w - padding.right, y)
    ctx.stroke()
    if (i > 0) {
      ctx.fillStyle = '#80868b'
      ctx.font = '10px sans-serif'
      ctx.textAlign = 'right'
      ctx.textBaseline = 'middle'
      ctx.fillText(String(i * 20), padding.left - 6, y)
    }
  }

  const groupWidth = chartW / personalities.length
  const barWidth = Math.max(8, Math.min(18, (groupWidth - 6) / companiesList.length))
  const barGap = Math.max(2, barWidth * 0.15)
  const radius = Math.min(barWidth * 0.35, 4)

  personalities.forEach((personality, pi) => {
    const groupX = padding.left + pi * groupWidth + groupWidth / 2
    ctx.save()
    ctx.translate(groupX, h - padding.bottom + 16)
    ctx.fillStyle = '#5f6368'
    ctx.font = '10px sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'bottom'
    ctx.fillText(personality, 0, 0)
    ctx.restore()

    companiesList.forEach((company, ci) => {
      const scores = personalityScores[personality] || {}
      let value = scores[company]
      if (value === undefined || value === null) value = 0
      const barH = Math.max(0, (value / 100) * chartH)
      const x = groupX + (ci - (companiesList.length - 1) / 2) * (barWidth + barGap) - barWidth / 2
      const y = padding.top + chartH - barH
      const rgb = colors[ci % colors.length]
      const grad = ctx.createLinearGradient(x, y, x, y + barH)
      grad.addColorStop(0, `rgba(${rgb[0]},${rgb[1]},${rgb[2]},1)`)
      grad.addColorStop(1, `rgba(${rgb[0]},${rgb[1]},${rgb[2]},0.65)`)
      ctx.fillStyle = grad
      if (radius < barH / 2 && barH > radius * 2) {
        ctx.beginPath()
        ctx.moveTo(x + radius, y)
        ctx.lineTo(x + barWidth - radius, y)
        ctx.quadraticCurveTo(x + barWidth, y, x + barWidth, y + radius)
        ctx.lineTo(x + barWidth, y + barH)
        ctx.lineTo(x, y + barH)
        ctx.lineTo(x, y + radius)
        ctx.quadraticCurveTo(x, y, x + radius, y)
        ctx.fill()
      } else {
        ctx.fillRect(x, y, barWidth, barH)
      }
      if (value >= 15) {
        ctx.fillStyle = '#202124'
        ctx.font = 'bold 9px sans-serif'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'bottom'
        ctx.fillText(String(Math.round(value)), x + barWidth / 2, y - 2)
      }
    })
  })

  if (companiesList.length > 0) {
    const legendX = w - padding.right + 8
    let legendY = padding.top + 4
    ctx.fillStyle = '#5f6368'
    ctx.font = 'bold 11px sans-serif'
    ctx.textAlign = 'left'
    ctx.textBaseline = 'top'
    ctx.fillText('公司', legendX, legendY)
    legendY += 18
    companiesList.forEach((company, ci) => {
      const rgb = colors[ci % colors.length]
      ctx.fillStyle = `rgba(${rgb[0]},${rgb[1]},${rgb[2]},1)`
      ctx.fillRect(legendX, legendY, 13, 12)
      ctx.fillStyle = '#3c4043'
      ctx.font = '11px sans-serif'
      ctx.textAlign = 'left'
      ctx.textBaseline = 'middle'
      ctx.fillText(company, legendX + 19, legendY + 6)
      legendY += 20
    })
  }
}

watch(() => props.careerResult, (val) => {
  if (val) {
    nextTick(() => drawCareerBarChart(val))
  }
})
</script>

<style scoped>
.career-modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.career-modal {
  background: #fff;
  border-radius: 16px;
  padding: 28px;
  width: 90%;
  max-width: 900px;
  max-height: 85vh;
  overflow-y: auto;
}

.career-close-btn {
  position: absolute;
  top: 16px;
  right: 18px;
  background: #f5f5f5;
  border: none;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  font-size: 18px;
  cursor: pointer;
  color: #888;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.career-close-btn:hover {
  background: #eee;
  color: #333;
}

.career-modal h2 {
  font-size: 20px;
  color: #1a1a2e;
  margin-bottom: 16px;
}

.career-input-area {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.career-input-area input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
}

.career-input-area input:focus {
  border-color: #4d6bfe;
}

.career-input-area button {
  padding: 8px 16px;
  background: #4d6bfe;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.career-input-area button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.company-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.company-tag {
  background: #f0f0ff;
  color: #4d6bfe;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.company-tag button {
  background: none;
  border: none;
  color: #4d6bfe;
  cursor: pointer;
  font-size: 14px;
  padding: 0;
}

.chart-container {
  margin-top: 16px;
}

.chart-container h3 {
  font-size: 14px;
  color: #333;
  margin-bottom: 8px;
}

.chart-container canvas {
  width: 100%;
  height: 350px;
}

.analysis-content {
  margin-top: 20px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.markdown-body {
  font-size: 14px;
  line-height: 1.8;
  color: #333;
}

.download-excel-btn {
  margin-top: 16px;
  padding: 10px 20px;
  background: #fff;
  color: #4d6bfe;
  border: 1px solid #4d6bfe;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.download-excel-btn:hover {
  background: #4d6bfe;
  color: #fff;
}
</style>

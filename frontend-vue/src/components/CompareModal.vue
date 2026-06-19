<template>
  <div class="compare-modal-overlay" @click.self="$emit('close')">
    <div class="compare-modal" style="position: relative;">
      <button class="compare-close-btn" @click="$emit('close')">&times;</button>
      <h2>📈 公司财务指标对比</h2>

      <div class="compare-input-area">
        <input v-model="companyInput" placeholder="输入公司名称，按回车添加"
            @keydown.enter.prevent="addCompany">
        <input v-model="yearInput" placeholder="年份（如2021，可选）" style="width: 150px;">
        <button @click="doCompare" :disabled="companies.length === 0 || compareLoading">
          {{ compareLoading ? '分析中...' : '开始对比' }}
        </button>
      </div>

      <div class="company-tags">
        <span v-for="(c, idx) in companies" :key="idx" class="company-tag">
          {{ c }}
          <button @click="removeCompany(idx)">&times;</button>
        </span>
      </div>

      <div v-if="compareError" style="color: #d93025; margin-bottom: 12px;">{{ compareError }}</div>

      <div v-if="compareResult && compareResult.not_found && compareResult.not_found.length > 0" style="margin-bottom: 16px;">
        <div v-for="(nf, idx) in compareResult.not_found" :key="idx"
             style="background:#fef7e0;border-left:4px solid #f9ab00;padding:10px 14px;margin-bottom:8px;border-radius:0 6px 6px 0;font-size:13px;color:#5f4c00;display:flex;align-items:center;gap:8px;">
          <span>⚠️</span>
          <span>{{ nf.reason }}</span>
        </div>
      </div>

      <div v-if="compareResult" class="compare-charts">
        <div class="chart-container" style="cursor:pointer;position:relative;" @click="openRadarZoom">
          <h3>财务能力雷达图 <span style="font-size:11px;color:#80868b;font-weight:normal;">(点击放大)</span></h3>
          <canvas ref="radarCanvas"></canvas>
        </div>
        <div class="chart-container">
          <h3>净利润趋势</h3>
          <canvas ref="lineCanvas"></canvas>
        </div>
      </div>

      <!-- 雷达图放大弹窗 -->
      <div v-if="showRadarZoom" class="radar-zoom-overlay" @click.self="closeRadarZoom">
        <div class="radar-zoom-content">
          <button class="radar-zoom-close" @click="closeRadarZoom">✕</button>
          <h3 style="text-align:center;margin-bottom:16px;color:#1f2937;">财务能力雷达图 - 详细视图</h3>
          <canvas ref="radarZoomCanvas"></canvas>
          <p style="text-align:center;margin-top:12px;color:#5f6368;font-size:12px;">鼠标悬浮查看具体数值 | 点击空白处关闭</p>
        </div>
      </div>

      <!-- 详细指标表格 -->
      <div v-if="compareResult && compareResult.companies && compareResult.companies.length > 0" class="metrics-table-container" style="margin-top: 20px; overflow-x: auto;">
        <h3 style="margin-bottom: 12px; color: #4d6bfe;">📊 详细财务指标对比</h3>
        <table class="metrics-table" style="width: 100%; border-collapse: collapse; font-size: 13px;">
          <thead>
            <tr style="background: #e8f0fe;">
              <th style="padding: 10px; border: 1px solid #dadce0; text-align: left;">指标</th>
              <th v-for="c in compareResult.companies" :key="c" style="padding: 10px; border: 1px solid #dadce0; text-align: center;">{{ c }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="metric in metrics" :key="metric.key" style="border-bottom: 1px solid #eee;">
              <td style="padding: 8px 10px; border: 1px solid #dadce0; font-weight: 500;">{{ metric.label }}</td>
              <td v-for="c in compareResult.companies" :key="c" style="padding: 8px 10px; border: 1px solid #dadce0; text-align: center;">
                {{ formatMetricValue(metric.key, c) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'

const props = defineProps({
  compareResult: { type: Object, default: null },
  compareLoading: { type: Boolean, default: false },
  compareError: { type: String, default: '' },
})

const emit = defineEmits(['close', 'compare'])

const companyInput = ref('')
const yearInput = ref('')
const companies = ref([])
const showRadarZoom = ref(false)
const radarCanvas = ref(null)
const lineCanvas = ref(null)
const radarZoomCanvas = ref(null)

const metrics = [
  { key: 'current_ratio', label: '流动比率' },
  { key: 'quick_ratio', label: '速动比率' },
  { key: 'cash_short_loan_ratio', label: '货币资金/短期借款' },
  { key: 'debt_ratio', label: '资产负债率' },
  { key: 'gross_margin', label: '毛利率' },
  { key: 'net_margin', label: '净利率' },
  { key: 'roe', label: 'ROE' },
  { key: 'revenue_growth', label: '营收增长率' },
  { key: 'non_recurring_profit_ratio', label: '非经常性损益占比' },
  { key: 'per_capita_salary', label: '人均薪酬' },
]

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

function doCompare() {
  emit('compare', { companies: [...companies.value], year: yearInput.value })
}

function formatMetricValue(key, company) {
  if (!props.compareResult) return '-'
  const calcData = props.compareResult.calculations || {}
  const companyCalc = calcData[company] || {}
  let rawVal = companyCalc[key]

  if (rawVal !== undefined && rawVal !== null && rawVal !== '' && rawVal !== '无' && rawVal !== '无数据' && rawVal !== '无短期借款') {
    const numVal = parseFloat(String(rawVal).replace(/,/g, ''))
    if (!isNaN(numVal)) {
      if (key === 'per_capita_salary') return '¥' + (numVal / 10000).toFixed(1) + '万'
      if (['debt_ratio', 'gross_margin', 'net_margin', 'roe', 'revenue_growth', 'non_recurring_profit_ratio'].includes(key)) return numVal.toFixed(2) + '%'
      if (['current_ratio', 'quick_ratio', 'cash_short_loan_ratio'].includes(key)) return numVal.toFixed(2) + '倍'
      return numVal.toFixed(2)
    }
    return String(rawVal)
  }
  if (rawVal === '无短期借款') return '无短期借款'
  if (rawVal === '无数据') return '无数据'
  if (rawVal === '无') return '-'
  return '-'
}

function openRadarZoom() {
  showRadarZoom.value = true
  nextTick(() => {
    if (props.compareResult) {
      drawRadarChart(props.compareResult, radarZoomCanvas.value)
    }
  })
}

function closeRadarZoom() {
  showRadarZoom.value = false
}

// 绘图相关
const palette = [
  { fill: 'rgba(26,115,232,0.18)', stroke: '#1a73e8', dot: '#1a73e8', glow: 'rgba(26,115,232,0.3)' },
  { fill: 'rgba(227,116,0,0.18)', stroke: '#e37400', dot: '#e37400', glow: 'rgba(227,116,0,0.3)' },
  { fill: 'rgba(24,128,56,0.18)', stroke: '#188038', dot: '#188038', glow: 'rgba(24,128,56,0.3)' },
  { fill: 'rgba(217,48,37,0.18)', stroke: '#d93025', dot: '#d93025', glow: 'rgba(217,48,37,0.3)' },
  { fill: 'rgba(147,52,230,0.18)', stroke: '#9334e6', dot: '#9334e6', glow: 'rgba(147,52,230,0.3)' },
]

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.lineTo(x + w - r, y)
  ctx.quadraticCurveTo(x + w, y, x + w, y + r)
  ctx.lineTo(x + w, y + h - r)
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h)
  ctx.lineTo(x + r, y + h)
  ctx.quadraticCurveTo(x, y + h, x, y + h - r)
  ctx.lineTo(x, y + r)
  ctx.quadraticCurveTo(x, y, x + r, y)
  ctx.closePath()
}

function drawRadarChart(data, canvas) {
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const dpr = window.devicePixelRatio || 1
  const container = canvas.parentElement
  const containerW = container ? container.clientWidth - 32 : 700
  const w = Math.min(containerW, 800)
  const h = Math.round(w * 0.65)
  canvas.width = w * dpr
  canvas.height = h * dpr
  canvas.style.width = w + 'px'
  canvas.style.height = h + 'px'
  ctx.scale(dpr, dpr)

  const cx = w / 2
  const cy = h / 2 + 10
  const radius = Math.min(w, h) / 2 - 60

  ctx.clearRect(0, 0, w, h)

  const companies = data.companies || []
  const radarData = data.radar_data || {}

  let allMetrics = new Set()
  companies.forEach(company => {
    if (radarData[company]) Object.keys(radarData[company]).forEach(m => allMetrics.add(m))
  })
  const metricsList = Array.from(allMetrics)
  if (metricsList.length === 0) return

  const angleStep = (Math.PI * 2) / metricsList.length

  for (let level = 1; level <= 5; level++) {
    ctx.beginPath()
    ctx.strokeStyle = level === 5 ? '#c5c9cc' : '#e8eaed'
    ctx.lineWidth = level === 5 ? 1.5 : 1
    for (let i = 0; i < metricsList.length; i++) {
      const angle = i * angleStep - Math.PI / 2
      const r = radius * level / 5
      const x = cx + Math.cos(angle) * r
      const y = cy + Math.sin(angle) * r
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    }
    ctx.closePath()
    ctx.stroke()
  }

  for (let i = 0; i < metricsList.length; i++) {
    const angle = i * angleStep - Math.PI / 2
    ctx.beginPath()
    ctx.strokeStyle = '#cfd4d9'
    ctx.lineWidth = 0.6
    ctx.setLineDash([3, 3])
    ctx.moveTo(cx, cy)
    ctx.lineTo(cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius)
    ctx.stroke()
    ctx.setLineDash([])

    const labelRadius = radius + 35
    const labelX = cx + Math.cos(angle) * labelRadius
    const labelY = cy + Math.sin(angle) * labelRadius
    ctx.fillStyle = '#1f2937'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    const labelText = metricsList[i]
    if (labelText.length > 5) {
      ctx.font = 'bold 9px sans-serif'
      const mid = Math.floor(labelText.length / 2)
      ctx.fillText(labelText.substring(0, mid), labelX, labelY - 7)
      ctx.fillText(labelText.substring(mid), labelX, labelY + 7)
    } else {
      ctx.font = 'bold 12px sans-serif'
      ctx.fillText(labelText, labelX, labelY)
    }
  }

  const pointCoords = []
  companies.forEach((company, ci) => {
    const values = radarData[company]
    if (!values || Object.keys(values).length === 0) return
    const style = palette[ci % palette.length]
    const pts = []

    for (let i = 0; i < metricsList.length; i++) {
      const angle = i * angleStep - Math.PI / 2
      let val = values[metricsList[i]]
      if (val === undefined || val === null || isNaN(val)) val = 0
      val = Math.max(0, Math.min(100, Number(val)))
      const r = radius * val / 100
      const x = cx + Math.cos(angle) * r
      const y = cy + Math.sin(angle) * r
      pts.push({ x, y, val, angle })
    }

    ctx.save()
    ctx.shadowColor = style.glow
    ctx.shadowBlur = 12
    ctx.beginPath()
    ctx.fillStyle = style.fill
    ctx.strokeStyle = style.stroke
    ctx.lineWidth = 2.8
    ctx.lineJoin = 'round'
    pts.forEach((p, idx) => { if (idx === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y) })
    ctx.closePath()
    ctx.fill()
    ctx.stroke()
    ctx.restore()

    ctx.beginPath()
    ctx.fillStyle = style.fill
    pts.forEach((p, idx) => { if (idx === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y) })
    ctx.closePath()
    ctx.fill()

    pts.forEach((p, idx) => {
      ctx.beginPath()
      ctx.arc(p.x, p.y, 5.5, 0, Math.PI * 2)
      ctx.fillStyle = '#fff'
      ctx.fill()
      ctx.strokeStyle = style.stroke
      ctx.lineWidth = 2.5
      ctx.stroke()
      ctx.beginPath()
      ctx.arc(p.x, p.y, 2.5, 0, Math.PI * 2)
      ctx.fillStyle = style.dot
      ctx.fill()
      pointCoords.push({ company, ci, x: p.x, y: p.y, val: p.val, angle: p.angle, color: style.stroke, idx })
    })
  })

  canvas._radarPoints = pointCoords
  canvas._radarMetrics = metricsList

  // Legend
  const itemW = 120
  const totalLegendW = companies.length * itemW + (companies.length - 1) * 16
  const legendStartX = (w - totalLegendW) / 2
  const legendY = 10
  companies.forEach((company, ci) => {
    const style = palette[ci % palette.length]
    const lx = legendStartX + ci * (itemW + 16)
    ctx.fillStyle = 'rgba(255,255,255,0.92)'
    roundRect(ctx, lx, legendY, itemW, 28, 6)
    ctx.fill()
    ctx.strokeStyle = '#e2e4e7'
    ctx.lineWidth = 1
    roundRect(ctx, lx, legendY, itemW, 28, 6)
    ctx.stroke()
    ctx.beginPath()
    ctx.arc(lx + 16, legendY + 14, 6, 0, Math.PI * 2)
    ctx.fillStyle = style.fill
    ctx.fill()
    ctx.strokeStyle = style.stroke
    ctx.lineWidth = 2
    ctx.stroke()
    ctx.beginPath()
    ctx.arc(lx + 16, legendY + 14, 2.5, 0, Math.PI * 2)
    ctx.fillStyle = style.dot
    ctx.fill()
    ctx.fillStyle = '#1f2937'
    ctx.font = 'bold 12px sans-serif'
    ctx.textAlign = 'left'
    ctx.textBaseline = 'middle'
    let displayName = company
    if (displayName.length > 5) displayName = company.substring(0, 5) + '..'
    ctx.fillText(displayName, lx + 28, legendY + 14)
  })
}

function drawLineChart(data) {
  const canvas = lineCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const dpr = window.devicePixelRatio || 1
  const rect = canvas.getBoundingClientRect()
  canvas.width = rect.width * dpr
  canvas.height = rect.height * dpr
  ctx.scale(dpr, dpr)

  const w = rect.width
  const h = rect.height
  const padding = { top: 30, right: 30, bottom: 40, left: 55 }
  const chartW = w - padding.left - padding.right
  const chartH = h - padding.top - padding.bottom

  ctx.clearRect(0, 0, w, h)

  const companies = data.companies || []
  const trendData = data.gross_margin_trend || {}
  const years = data.years || []

  if (years.length === 0) {
    ctx.fillStyle = '#5f6368'
    ctx.font = '14px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('暂无净利润数据', w / 2, h / 2)
    return
  }

  let maxVal = 0, minVal = Infinity
  companies.forEach(c => {
    const vals = trendData[c] || []
    vals.forEach(v => { if (v > maxVal) maxVal = v; if (v < minVal) minVal = v })
  })
  if (maxVal === 0 && minVal === Infinity) maxVal = 100
  if (minVal === Infinity) minVal = 0
  if (minVal > 0) minVal = 0
  if (maxVal <= 0) maxVal = Math.abs(minVal) + 1

  const valRange = maxVal - minVal
  const step = Math.max(1, Math.pow(10, Math.floor(Math.log10(valRange))))
  const finalMax = Math.ceil(maxVal / step) * step
  const finalMin = Math.min(Math.floor(minVal / step) * step, 0)
  const range = finalMax - finalMin || 1

  const colors = ['#1a73e8', '#e37400', '#188038', '#d93025', '#9334e6']

  ctx.strokeStyle = '#e0e0e0'
  ctx.lineWidth = 1
  for (let i = 0; i <= 5; i++) {
    const y = padding.top + chartH * i / 5
    ctx.beginPath()
    ctx.moveTo(padding.left, y)
    ctx.lineTo(padding.left + chartW, y)
    ctx.stroke()
    ctx.fillStyle = '#5f6368'
    ctx.font = '11px sans-serif'
    ctx.textAlign = 'right'
    ctx.textBaseline = 'middle'
    ctx.fillText((finalMax - range * i / 5).toFixed(0), padding.left - 8, y)
  }

  years.forEach((year, i) => {
    const x = padding.left + chartW * i / (years.length - 1 || 1)
    ctx.fillStyle = '#5f6368'
    ctx.font = '12px sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'
    ctx.fillText(year, x, padding.top + chartH + 10)
  })

  if (finalMin < 0) {
    const zeroY = padding.top + chartH * (finalMax / range)
    ctx.beginPath()
    ctx.strokeStyle = '#9aa0a6'
    ctx.lineWidth = 1.2
    ctx.setLineDash([4, 3])
    ctx.moveTo(padding.left, zeroY)
    ctx.lineTo(padding.left + chartW, zeroY)
    ctx.stroke()
    ctx.setLineDash([])
  }

  companies.forEach((company, ci) => {
    const vals = trendData[company] || []
    if (vals.length === 0) return
    ctx.beginPath()
    ctx.strokeStyle = colors[ci % colors.length]
    ctx.lineWidth = 2.5
    vals.forEach((val, i) => {
      const x = padding.left + chartW * i / (years.length - 1 || 1)
      const y = padding.top + chartH * (1 - (val - finalMin) / range)
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
    })
    ctx.stroke()
    vals.forEach((val, i) => {
      const x = padding.left + chartW * i / (years.length - 1 || 1)
      const y = padding.top + chartH * (1 - (val - finalMin) / range)
      ctx.beginPath()
      ctx.fillStyle = colors[ci % colors.length]
      ctx.arc(x, y, 4, 0, Math.PI * 2)
      ctx.fill()
    })
  })
}

// 当结果变化时重绘图表
watch(() => props.compareResult, (val) => {
  if (val) {
    nextTick(() => {
      drawRadarChart(val, radarCanvas.value)
      drawLineChart(val)
      setupRadarHover(radarCanvas.value)
    })
  }
})

let radarTooltipEl = null
function getRadarTooltipEl() {
  if (!radarTooltipEl) {
    radarTooltipEl = document.createElement('div')
    radarTooltipEl.style.cssText = 'position:fixed;pointer-events:none;z-index:9999;display:none;padding:6px 12px;background:#1f2937;color:#fff;font-size:12px;font-weight:bold;border-radius:6px;box-shadow:0 4px 12px rgba(0,0,0,0.25);white-space:nowrap;'
    document.body.appendChild(radarTooltipEl)
  }
  return radarTooltipEl
}

function setupRadarHover(canvas) {
  if (!canvas) return
  const tooltip = getRadarTooltipEl()
  canvas.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top
    const points = canvas._radarPoints || []
    const metricsList = canvas._radarMetrics || []
    let closest = null
    let minDist = 20
    points.forEach(p => {
      const dx = mx - p.x
      const dy = my - p.y
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < minDist) { minDist = dist; closest = p }
    })
    if (closest) {
      const metricName = metricsList[closest.idx] || ''
      tooltip.innerHTML = `<span style="color:${closest.color}">●</span> <b>${closest.company}</b><br>${metricName}: <b style="color:${closest.color}">${Math.round(closest.val)}</b>分`
      tooltip.style.display = 'block'
      tooltip.style.left = (e.clientX + 16) + 'px'
      tooltip.style.top = (e.clientY + 12) + 'px'
      canvas.style.cursor = 'pointer'
    } else {
      tooltip.style.display = 'none'
      canvas.style.cursor = 'default'
    }
  })
  canvas.addEventListener('mouseleave', () => {
    tooltip.style.display = 'none'
    canvas.style.cursor = 'default'
  })
}
</script>

<style scoped>
.compare-modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.compare-modal {
  background: #fff;
  border-radius: 16px;
  padding: 28px;
  width: 90%;
  max-width: 900px;
  max-height: 85vh;
  overflow-y: auto;
}

.compare-close-btn {
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

.compare-close-btn:hover {
  background: #eee;
  color: #333;
}

.compare-modal h2 {
  font-size: 20px;
  color: #1a1a2e;
  margin-bottom: 16px;
}

.compare-input-area {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.compare-input-area input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
}

.compare-input-area input:focus {
  border-color: #4d6bfe;
}

.compare-input-area button {
  padding: 8px 16px;
  background: #4d6bfe;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.compare-input-area button:disabled {
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

.compare-charts {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  margin-top: 16px;
}

.chart-container {
  flex: 1;
  min-width: 300px;
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

.radar-zoom-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.65);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  animation: fadeIn 0.2s ease-out;
}

.radar-zoom-content {
  background: #fff;
  border-radius: 16px;
  padding: 28px;
  width: 92%;
  max-width: 780px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
  position: relative;
  animation: zoomIn 0.25s ease-out;
}

.radar-zoom-close {
  position: absolute;
  top: 16px;
  right: 18px;
  background: #f5f5f5;
  border: none;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  font-size: 16px;
  color: #888;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  z-index: 10;
}

.radar-zoom-close:hover {
  background: #eee;
  color: #333;
}

.radar-zoom-content canvas {
  width: 100% !important;
  height: 560px !important;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes zoomIn {
  from { transform: scale(0.9); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}
</style>

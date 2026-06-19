<template>
  <view class="page">
    <view class="header">
      <text class="title">公司对比分析</text>
      <text class="subtitle">选择公司进行横向对比</text>
    </view>

    <view class="form-card">
      <view class="form-item">
        <text class="label">对比公司</text>
        <input class="input" type="text" v-model="companiesText" placeholder="多个公司用逗号分隔" />
      </view>
      <view class="form-item">
        <text class="label">年份</text>
        <input class="input" type="number" v-model="year" placeholder="如：2023" />
      </view>
    </view>

    <view class="submit-btn" :class="{ active: canSubmit }" @click="doCompare">
      <text>{{ loading ? '分析中...' : '开始对比' }}</text>
    </view>

    <view v-if="structuredResult && structuredResult.companies.length > 0" class="charts-section">
      <view class="chart-card">
        <text class="chart-title">财务能力雷达图</text>
        <text class="chart-hint">双指缩放 / 单指拖动</text>
        <view class="chart-zoom-wrap"
          @touchstart="onTouchStart($event, 'radar')"
          @touchmove="onTouchMove($event, 'radar')"
          @touchend="onTouchEnd($event, 'radar')"
        >
          <canvas canvas-id="radarCanvas" class="radar-canvas"></canvas>
        </view>
        <view class="chart-toolbar">
          <view class="tool-btn" @click="resetZoom('radar')"><text>重置</text></view>
          <view class="tool-btn" @click="zoomIn('radar')"><text>+</text></view>
          <view class="tool-btn" @click="zoomOut('radar')"><text>-</text></view>
        </view>
        <view class="legend-row">
          <view v-for="(company, ci) in structuredResult.companies" :key="'leg-' + company" class="legend-item">
            <view class="legend-dot" :style="{ background: palette[ci % palette.length].stroke }"></view>
            <text class="legend-text">{{ company }}</text>
          </view>
        </view>
      </view>

      <view v-if="hasTrendData" class="chart-card">
        <text class="chart-title">净利润趋势（万元）</text>
        <text class="chart-hint">双指缩放 / 单指拖动</text>
        <view class="chart-zoom-wrap"
          @touchstart="onTouchStart($event, 'line')"
          @touchmove="onTouchMove($event, 'line')"
          @touchend="onTouchEnd($event, 'line')"
        >
          <canvas canvas-id="lineCanvas" class="line-canvas"></canvas>
        </view>
        <view class="chart-toolbar">
          <view class="tool-btn" @click="resetZoom('line')"><text>重置</text></view>
          <view class="tool-btn" @click="zoomIn('line')"><text>+</text></view>
          <view class="tool-btn" @click="zoomOut('line')"><text>-</text></view>
        </view>
        <view class="legend-row">
          <view v-for="(company, ci) in structuredResult.companies" :key="'lleg-' + company" class="legend-item">
            <view class="legend-line" :style="{ background: lineColors[ci % lineColors.length] }"></view>
            <text class="legend-text">{{ company }}</text>
          </view>
        </view>
      </view>
    </view>

    <view v-if="structuredResult" class="result-card">
      <text class="result-title">财务指标详情</text>
      <view v-for="company in structuredResult.companies" :key="company" class="company-section">
        <text class="company-name">{{ company }}</text>
        <view v-if="structuredResult.calculations[company]" class="calc-list">
          <view v-for="(value, key) in structuredResult.calculations[company]" :key="key" class="calc-item">
            <text class="calc-key">{{ labelMap[key] || key }}</text>
            <text class="calc-val">{{ value }}</text>
          </view>
        </view>
        <text v-else class="no-data">暂无计算数据</text>
      </view>
      <view v-if="structuredResult.not_found && structuredResult.not_found.length" class="not-found-section">
        <text class="section-label">未找到数据：</text>
        <view v-for="item in structuredResult.not_found" :key="item.company" class="not-found-item">
          <text>{{ item.company }}: {{ item.reason }}</text>
        </view>
      </view>
    </view>

    <view v-if="error" class="error-box">
      <text>{{ error }}</text>
    </view>
  </view>
</template>

<script>
import { ref, computed, nextTick } from 'vue'
import { compareCompanies } from '../../utils/api.js'

export default {
  data() {
    return {
      companiesText: '',
      year: '',
      loading: false,
      result: '',
      error: '',
      structuredResult: null,
      labelMap: {
        'current_ratio': '流动比率',
        'quick_ratio': '速动比率',
        'cash_short_loan_ratio': '货币资金/短期借款',
        'debt_ratio': '资产负债率(%)',
        'gross_margin': '毛利率(%)',
        'net_margin': '净利率(%)',
        'roe': '净资产收益率(%)',
        'revenue_growth': '营收增长率(%)',
        'non_recurring_profit_ratio': '非经常性损益占比(%)',
        'per_capita_salary': '人均薪酬(元)',
        'eps': '每股收益EPS(元)',
        'bps': '每股净资产BPS(元)',
        'total_shares': '总股本(股)'
      },
      palette: [
        { stroke: '#1565c0', fill: 'rgba(21,101,192,0.15)', glow: 'rgba(21,101,192,0.35)', dot: '#1565c0' },
        { stroke: '#e65100', fill: 'rgba(230,81,0,0.12)', glow: 'rgba(230,81,0,0.30)', dot: '#e65100' },
        { stroke: '#2e7d32', fill: 'rgba(46,125,50,0.12)', glow: 'rgba(46,125,50,0.30)', dot: '#2e7d32' },
        { stroke: '#c62828', fill: 'rgba(198,40,40,0.12)', glow: 'rgba(198,40,40,0.30)', dot: '#c62828' }
      ],
      lineColors: ['#1a73e8', '#e37400', '#188038', '#d93025'],
      // 缩放/平移状态
      radarScale: 1, radarX: 0, radarY: 0,
      lineScale: 1, lineX: 0, lineY: 0,
      // 触摸状态
      touchStartDist: 0, touchStartScale: 1,
      touchStartX: 0, touchStartY: 0,
      touchStartTransX: 0, touchStartTransY: 0,
      touchType: '' // 'radar' or 'line'
    }
  },
  computed: {
    canSubmit() {
      return this.companiesText.trim() && this.year.toString().trim()
    },
    hasTrendData() {
      if (!this.structuredResult) return false
      var trend = this.structuredResult.gross_margin_trend || {}
      var keys = Object.keys(trend)
      for (var k = 0; k < keys.length; k++) {
        var arr = trend[keys[k]]
        if (arr && arr.length > 0) return true
      }
      return false
    }
  },
  methods: {
    doCompare: function() {
      var self = this
      if (!self.canSubmit || self.loading) return

      self.loading = true
      self.result = ''
      self.error = ''
      self.structuredResult = null

      var companies = self.companiesText.split(/[,，]/).map(function(s) { return s.trim() }).filter(Boolean)

      uni.showLoading({ title: '分析中...' })
      compareCompanies(companies, self.year).then(function(data) {
        uni.hideLoading()

        if (data.error) {
          self.error = data.error
        } else if (data.result) {
          self.result = data.result
        } else if (data.companies && data.companies.length > 0) {
          self.structuredResult = data
          if (data.not_found && data.not_found.length === companies.length) {
            self.error = '所有公司均未找到财报数据'
          }
          nextTick(function() {
            setTimeout(function() {
              self.drawRadarChart(data)
              self.drawLineChart(data)
            }, 300)
          })
        } else if (Object.keys(data).length > 0) {
          self.structuredResult = data
        } else {
          self.error = '未返回有效结果'
        }
      }).catch(function(e) {
        uni.hideLoading()
        self.error = '请求失败: ' + e.message
      }).finally(function() {
        self.loading = false
      })
    },

    drawRadarChart: function(data) {
      var self = this
      setTimeout(function() {
        var query = uni.createSelectorQuery().in(self)
        query.select('.radar-canvas').boundingClientRect(function(rect) {
          if (!rect || !rect.width) {
            console.log('radarCanvas rect not found')
            return
          }
          // 旧 API：不需要 pixelRatio，直接按 CSS 像素绘制
          var w = rect.width
          var h = rect.height
          if (w < 10 || h < 10) return

          var ctx = uni.createCanvasContext('radarCanvas', self)

          var companies = data.companies || []
          var radarData = data.radar_data || {}
          var allMetricsSet = {}
          var metrics = []

          for (var ci = 0; ci < companies.length; ci++) {
            var c = companies[ci]
            if (radarData[c]) {
              var keys = Object.keys(radarData[c])
              for (var ki = 0; ki < keys.length; ki++) {
                allMetricsSet[keys[ki]] = 1
              }
            }
          }
          metrics = Object.keys(allMetricsSet)
          if (metrics.length === 0) {
            ctx.draw()
            return
          }

          var angleStep = (Math.PI * 2) / metrics.length
          var cx = w / 2
          var cy = h / 2
          var labelSpace = Math.max(32, w * 0.11)
          var radius = Math.min(w, h) / 2 - labelSpace

          // 网格
          for (var level = 1; level <= 5; level++) {
            ctx.beginPath()
            ctx.setStrokeStyle(level === 5 ? '#9aa0a6' : '#e8eaed')
            ctx.setLineWidth(level === 5 ? 1 : 0.5)
            for (var mi = 0; mi < metrics.length; mi++) {
              var a = mi * angleStep - Math.PI / 2
              var r = radius * level / 5
              var px = cx + Math.cos(a) * r
              var py = cy + Math.sin(a) * r
              if (mi === 0) ctx.moveTo(px, py)
              else ctx.lineTo(px, py)
            }
            ctx.closePath()
            ctx.stroke()
            if (level === 5) {
              ctx.setFillStyle('rgba(243,245,248,0.7)')
              ctx.fill()
            }
          }

          // 轴线 + 标签
          var fs = Math.max(9, Math.min(12, w / 30))
          ctx.setFontSize(fs)
          ctx.setFillStyle('#333')
          ctx.setTextAlign('center')
          ctx.setTextBaseline('middle')

          for (var li = 0; li < metrics.length; li++) {
            var la = li * angleStep - Math.PI / 2
            ctx.beginPath()
            ctx.setStrokeStyle('#d0d4d9')
            ctx.setLineWidth(0.5)
            ctx.setLineDash([3, 3])
            ctx.moveTo(cx, cy)
            ctx.lineTo(cx + Math.cos(la) * radius, cy + Math.sin(la) * radius)
            ctx.stroke()
            ctx.setLineDash([])

            var lr = radius + labelSpace - 6
            var lx = cx + Math.cos(la) * lr
            var ly = cy + Math.sin(la) * lr
            var lt = metrics[li]
            ctx.setFontSize(fs)
            ctx.setFillStyle('#333')
            if (lt.length > 4) {
              var mid = Math.floor(lt.length / 2)
              ctx.fillText(lt.substring(0, mid), lx, ly - fs * 0.6)
              ctx.fillText(lt.substring(mid), lx, ly + fs * 0.6)
            } else {
              ctx.setFontSize(fs + 1)
              ctx.fillText(lt, lx, ly)
            }
          }

          // 数据多边形
          var pal = self.palette
          for (var di = 0; di < companies.length; di++) {
            var dc = companies[di]
            var vals = radarData[dc]
            if (!vals || Object.keys(vals).length === 0) continue
            var style = pal[di % pal.length]

            ctx.beginPath()
            for (var pi = 0; pi < metrics.length; pi++) {
              var pa = pi * angleStep - Math.PI / 2
              var pv = vals[metrics[pi]]
              if (pv === undefined || pv === null || isNaN(pv)) pv = 0
              pv = Math.max(0, Math.min(100, Number(pv)))
              var pr = radius * pv / 100
              if (pi === 0) ctx.moveTo(cx + Math.cos(pa) * pr, cy + Math.sin(pa) * pr)
              else ctx.lineTo(cx + Math.cos(pa) * pr, cy + Math.sin(pa) * pr)
            }
            ctx.closePath()
            ctx.setFillStyle(style.fill)
            ctx.fill()
            ctx.setStrokeStyle(style.stroke)
            ctx.setLineWidth(2)
            ctx.stroke()

            // 数据点
            for (var dpi = 0; dpi < metrics.length; dpi++) {
              var dpa = dpi * angleStep - Math.PI / 2
              var dpv = vals[metrics[dpi]]
              if (dpv === undefined || dpv === null || isNaN(dpv)) dpv = 0
              dpv = Math.max(0, Math.min(100, Number(dpv)))
              var dpr2 = radius * dpv / 100
              var dpx = cx + Math.cos(dpa) * dpr2
              var dpy = cy + Math.sin(dpa) * dpr2
              ctx.beginPath()
              ctx.arc(dpx, dpy, 3.5, 0, 2 * Math.PI)
              ctx.setFillStyle('#fff')
              ctx.fill()
              ctx.setStrokeStyle(style.stroke)
              ctx.setLineWidth(1.5)
              ctx.stroke()
            }
          }

          ctx.draw()
        }).exec()
      }, 500)
    },

    // 获取两点距离
    getTouchDist: function(t1, t2) {
      var dx = t1.clientX - t2.clientX
      var dy = t1.clientY - t2.clientY
      return Math.sqrt(dx * dx + dy * dy)
    },

    onTouchStart: function(e, type) {
      var touches = e.touches
      if (touches.length === 2) {
        // 双指：准备缩放
        this.touchStartDist = this.getTouchDist(touches[0], touches[1])
        this.touchStartScale = type === 'radar' ? this.radarScale : this.lineScale
        this.touchType = type
      } else if (touches.length === 1) {
        // 单指：准备拖动
        this.touchStartX = touches[0].clientX
        this.touchStartY = touches[0].clientY
        this.touchStartTransX = type === 'radar' ? this.radarX : this.lineX
        this.touchStartTransY = type === 'radar' ? this.radarY : this.lineY
        this.touchType = type
      }
    },

    onTouchMove: function(e, type) {
      e.preventDefault()
      var touches = e.touches
      if (type !== this.touchType) return

      if (touches.length === 2) {
        // 双指缩放
        var dist = this.getTouchDist(touches[0], touches[1])
        if (this.touchStartDist > 0) {
          var newScale = this.touchStartScale * (dist / this.touchStartDist)
          newScale = Math.max(0.5, Math.min(5, newScale))
          if (type === 'radar') this.radarScale = newScale
          else this.lineScale = newScale
        }
      } else if (touches.length === 1) {
        // 单指拖动
        var dx = touches[0].clientX - this.touchStartX
        var dy = touches[0].clientY - this.touchStartY
        if (type === 'radar') {
          this.radarX = this.touchStartTransX + dx / this.radarScale
          this.radarY = this.touchStartTransY + dy / this.radarScale
        } else {
          this.lineX = this.touchStartTransX + dx / this.lineScale
          this.lineY = this.touchStartTransY + dy / this.lineScale
        }
      }
    },

    onTouchEnd: function(e, type) {
      this.touchType = ''
    },

    zoomIn: function(type) {
      if (type === 'radar') this.radarScale = Math.min(5, this.radarScale + 0.3)
      else this.lineScale = Math.min(5, this.lineScale + 0.3)
    },

    zoomOut: function(type) {
      if (type === 'radar') this.radarScale = Math.max(0.5, this.radarScale - 0.3)
      else this.lineScale = Math.max(0.5, this.lineScale - 0.3)
    },

    resetZoom: function(type) {
      if (type === 'radar') { this.radarScale = 1; this.radarX = 0; this.radarY = 0 }
      else { this.lineScale = 1; this.lineX = 0; this.lineY = 0 }
    },

    drawLineChart: function(data) {
      var self = this
      setTimeout(function() {
        var query = uni.createSelectorQuery().in(self)
        query.select('.line-canvas').boundingClientRect(function(rect) {
          if (!rect || !rect.width) {
            console.log('lineCanvas rect not found')
            return
          }
          // 旧 API：直接按 CSS 像素绘制
          var w = rect.width
          var h = rect.height
          if (w < 10 || h < 10) return

          var ctx = uni.createCanvasContext('lineCanvas', self)

          var companies = data.companies || []
          var trendData = data.gross_margin_trend || {}
          var years = data.years || []

          var pad = { top: h * 0.1, right: w * 0.03, bottom: h * 0.15, left: w * 0.1 }
          var chartW = w - pad.left - pad.right
          var chartH = h - pad.top - pad.bottom

          if (years.length === 0) {
            ctx.setFillStyle('#999')
            ctx.setFontSize(12)
            ctx.setTextAlign('center')
            ctx.setTextBaseline('middle')
            ctx.fillText('暂无趋势数据', w / 2, h / 2)
            ctx.draw()
            return
          }

          var maxVal = 0
          var minVal = Infinity
          for (var ci = 0; ci < companies.length; ci++) {
            var cv = trendData[companies[ci]] || []
            for (var vi = 0; vi < cv.length; vi++) {
              if (cv[vi] > maxVal) maxVal = cv[vi]
              if (cv[vi] < minVal) minVal = cv[vi]
            }
          }
          if (maxVal === 0 && minVal === Infinity) maxVal = 100
          if (minVal === Infinity) minVal = 0
          if (minVal > 0) minVal = 0
          var range = maxVal - minVal || 1

          var fs = Math.max(8, Math.min(10, w / 35))

          // 网格线
          ctx.setStrokeStyle('#e8eaed')
          ctx.setLineWidth(0.5)
          for (var gi = 0; gi <= 4; gi++) {
            var gy = pad.top + chartH * gi / 4
            ctx.beginPath()
            ctx.moveTo(pad.left, gy)
            ctx.lineTo(pad.left + chartW, gy)
            ctx.stroke()
            ctx.setFontSize(fs)
            ctx.setFillStyle('#888')
            ctx.setTextAlign('right')
            ctx.setTextBaseline('middle')
            ctx.fillText(String(Math.round(maxVal - range * gi / 4)), pad.left - 3, gy)
          }

          // X轴年份
          ctx.setFontSize(fs)
          ctx.setFillStyle('#666')
          ctx.setTextAlign('center')
          ctx.setTextBaseline('top')
          for (var yi = 0; yi < years.length; yi++) {
            var xx = pad.left + chartW * yi / (years.length - 1 || 1)
            ctx.fillText(years[yi], xx, pad.top + chartH + 4)
          }

          // 零线
          if (minVal < 0) {
            var zy = pad.top + chartH * (maxVal / range)
            ctx.beginPath()
            ctx.setStrokeStyle('#bbb')
            ctx.setLineWidth(0.6)
            ctx.setLineDash([3, 2])
            ctx.moveTo(pad.left, zy)
            ctx.lineTo(pad.left + chartW, zy)
            ctx.stroke()
            ctx.setLineDash([])
          }

          // 折线
          var lcolors = self.lineColors
          for (var lci = 0; lci < companies.length; lci++) {
            var lc = companies[lci]
            var lvals = trendData[lc] || []
            if (lvals.length === 0) continue
            var color = lcolors[lci % lcolors.length]

            ctx.beginPath()
            ctx.setStrokeStyle(color)
            ctx.setLineWidth(1.8)
            ctx.setLineJoin('round')
            for (var lvi = 0; lvi < lvals.length; lvi++) {
              var lx = pad.left + chartW * lvi / (years.length - 1 || 1)
              var ly = pad.top + chartH * ((maxVal - lvals[lvi]) / range)
              if (lvi === 0) ctx.moveTo(lx, ly)
              else ctx.lineTo(lx, ly)
            }
            ctx.stroke()

            // 数据点
            for (var dp = 0; dp < lvals.length; dp++) {
              var dx = pad.left + chartW * dp / (years.length - 1 || 1)
              var dy = pad.top + chartH * ((maxVal - lvals[dp]) / range)
              ctx.beginPath()
              ctx.arc(dx, dy, 3, 0, 2 * Math.PI)
              ctx.setFillStyle('#fff')
              ctx.fill()
              ctx.setStrokeStyle(color)
              ctx.setLineWidth(1.2)
              ctx.stroke()
            }
          }

          ctx.draw()
        }).exec()
      }, 600)
    }
  }
}
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh;
  background: #f7f7f8;
  padding: 32rpx 24rpx;
}
.header {
  margin-bottom: 40rpx;
  .title { font-size: 40rpx; font-weight: 700; color: #333; display: block; }
  .subtitle { font-size: 26rpx; color: #999; margin-top: 8rpx; display: block; }
}
.form-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 32rpx;
  box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.06);
  margin-bottom: 32rpx;
  .form-item {
    margin-bottom: 28rpx;
    &:last-child { margin-bottom: 0; }
    .label { font-size: 28rpx; font-weight: 600; color: #333; display: block; margin-bottom: 16rpx; }
    .input { height: 88rpx; background: #f5f6fa; border-radius: 12rpx; padding: 0 24rpx; font-size: 28rpx; color: #333; }
  }
}
.submit-btn {
  height: 96rpx;
  border-radius: 48rpx;
  background: #ccc;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 32rpx;
  text { font-size: 30rpx; color: #fff; font-weight: 600; }
  &.active { background: linear-gradient(135deg, #4d6bfe 0%, #6b85ff 100%); &:active { opacity: 0.85; } }
}
.charts-section { margin-bottom: 32rpx; }
.chart-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 28rpx 20rpx;
  box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.06);
  margin-bottom: 24rpx;
  .chart-title { font-size: 28rpx; font-weight: 700; color: #333; display: block; margin-bottom: 8rpx; text-align: center; }
  .chart-hint { font-size: 20rpx; color: #bbb; display: block; text-align: center; margin-bottom: 12rpx; }
}
.chart-zoom-wrap {
  overflow: visible;
  width: 100%;
  position: relative;
}
.radar-canvas { width: 100%; height: 500rpx; display: block; }
.line-canvas { width: 100%; height: 360rpx; display: block; }
.chart-toolbar {
  display: flex;
  justify-content: center;
  gap: 16rpx;
  margin-top: 12rpx;
  .tool-btn {
    width: 64rpx;
    height: 64rpx;
    border-radius: 32rpx;
    background: #f0f2f5;
    display: flex;
    align-items: center;
    justify-content: center;
    &:active { background: #e0e3e8; }
    text { font-size: 28rpx; color: #333; font-weight: 600; }
  }
}
.legend-row {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 24rpx;
  margin-top: 16rpx;
  .legend-item {
    display: flex;
    align-items: center;
    gap: 8rpx;
    .legend-dot { width: 18rpx; height: 18rpx; border-radius: 50%; flex-shrink: 0; }
    .legend-line { width: 28rpx; height: 6rpx; border-radius: 3rpx; flex-shrink: 0; }
    .legend-text { font-size: 22rpx; color: #666; }
  }
}
.result-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 32rpx;
  box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.06);
  .result-title { font-size: 30rpx; font-weight: 600; color: #4d6bfe; display: block; margin-bottom: 20rpx; }
}
.error-box {
  background: #fef0f0;
  border-radius: 12rpx;
  padding: 24rpx;
  text { font-size: 26rpx; color: #f53f3f; }
}
.company-section {
  margin-bottom: 32rpx;
  padding-bottom: 28rpx;
  border-bottom: 1rpx solid #eee;
  &:last-child { border-bottom: none; margin-bottom: 0; }
  .company-name { font-size: 30rpx; font-weight: 700; color: #4d6bfe; display: block; margin-bottom: 16rpx; }
}
.calc-list {
  .calc-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12rpx 0;
    border-bottom: 1rpx solid #f5f5f5;
    .calc-key { font-size: 26rpx; color: #666; flex: 1; }
    .calc-val { font-size: 26rpx; color: #333; font-weight: 600; text-align: right; }
  }
}
.no-data { font-size: 26rpx; color: #999; font-style: italic; }
.not-found-section {
  margin-top: 24rpx;
  padding: 20rpx;
  background: #fff8e6;
  border-radius: 10rpx;
  .section-label { font-size: 26rpx; font-weight: 600; color: #e6a23c; display: block; margin-bottom: 12rpx; }
  .not-found-item { padding: 8rpx 0; text { font-size: 24rpx; color: #c08020; } }
}
</style>

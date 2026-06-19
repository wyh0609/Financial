<template>
  <view class="page">
    <view class="header">
      <text class="title">职业分析</text>
      <text class="subtitle">基于财报数据提供职业发展建议</text>
    </view>

    <!-- 表单 -->
    <view class="form-card">
      <view class="form-item">
        <text class="label">目标公司</text>
        <input
          class="input"
          type="text"
          v-model="companiesText"
          placeholder="多个公司用逗号分隔"
        />
      </view>

      <view class="form-item">
        <text class="label">年份</text>
        <input
          class="input"
          type="number"
          v-model="year"
          placeholder="如：2023"
        />
      </view>

      <!-- 上传PDF -->
      <view class="form-item">
        <text class="label">上传财报（可选）</text>
        <view class="upload-row">
          <!-- #ifdef H5 -->
          <view class="upload-btn" @click="triggerUpload">
            <text class="upload-icon">+</text>
            <text class="upload-text">{{ fileName || '选择PDF文件' }}</text>
          </view>
          <input
            ref="fileInput"
            type="file"
            accept=".pdf"
            style="display:none"
            @change="onFileChange"
          />
          <!-- #endif -->
          <!-- #ifndef H5 -->
          <view class="upload-btn" @click="pickFile">
            <text class="upload-icon">+</text>
            <text class="upload-text">{{ fileName || '选择PDF文件' }}</text>
          </view>
          <!-- #endif -->
        </view>
      </view>
    </view>

    <!-- 分析按钮 -->
    <view class="submit-btn" :class="{ active: canSubmit }" @click="doAnalyze">
      <text>{{ loading ? '分析中...' : '开始分析' }}</text>
    </view>

    <!-- 人格匹配度柱状图 -->
    <view v-if="personalityScores && companies.length > 0" class="chart-card">
      <text class="chart-title">📊 人格匹配度柱状图</text>
      <canvas
        canvas-id="barCanvas"
        class="bar-canvas"
        :style="{ width: '100%', height: '720rpx' }"
      ></canvas>
      <view class="legend-row">
        <view v-for="(company, ci) in companies" :key="'leg-' + company" class="legend-item">
          <view class="legend-dot" :style="{ background: barColors[ci % barColors.length] }"></view>
          <text class="legend-text">{{ company }}</text>
        </view>
      </view>
    </view>

    <!-- 结果 -->
    <view v-if="resultPart1 || personalityTableRows.length > 0" class="result-card">
      <view class="result-header">
        <text class="result-title">分析结果</text>
        <view v-if="personalityScores" class="download-btn" @click="downloadExcel">
          <text>下载Excel</text>
        </view>
      </view>

      <!-- 第三部分之前的内容 -->
      <rich-text v-if="resultPart1" class="result-content" :nodes="resultPart1"></rich-text>

      <!-- 人格得分表格（紧跟第三部分标题后） -->
      <view v-if="personalityTableRows.length > 0" class="native-table-wrap">
        <!-- 表头 -->
        <view class="table-header-row">
          <view class="table-cell th"><text>人格类型</text></view>
          <view v-for="(company, ci) in companies" :key="'th-' + company" class="table-cell th">
            <text>{{ company }}</text>
          </view>
        </view>
        <!-- 数据行 -->
        <scroll-view scroll-y class="table-body-scroll" :style="{ maxHeight: personalityTableRows.length * 72 + 'rpx' }">
          <view
            v-for="(row, ri) in personalityTableRows"
            :key="'tr-' + row.type"
            class="table-data-row"
            :style="{ background: ri % 2 === 0 ? '#f8f9ff' : '#ffffff' }"
          >
            <view class="table-cell td-type"><text>{{ row.type }}</text></view>
            <view v-for="(company, ci2) in companies" :key="'td-' + row.type + '-' + company" class="table-cell td-score">
              <text>{{ row.scores[company] !== undefined ? row.scores[company] : '-' }}</text>
            </view>
          </view>
        </scroll-view>
      </view>

      <!-- 第三部分之后的内容 -->
      <rich-text v-if="resultPart2" class="result-content" :nodes="resultPart2"></rich-text>
    </view>

    <view v-if="error" class="error-box">
      <text>{{ error }}</text>
    </view>
  </view>
</template>

<script>
import { renderMarkdown } from '../../utils/markdown.js'
import { BASE_URL } from '../../utils/api.js'

export default {
  data() {
    return {
      companiesText: '',
      year: '',
      loading: false,
      result: '',
      error: '',
      companies: [],
      personalityScores: null,
      personalityTableRows: [],
      resultPart1: '',
      resultPart2: '',
      _personalityTableHtml: '',
      fileName: '',
      filePath: '',
      // 柱状图颜色（与原始HTML一致）
      barColors: [
        'rgba(26,115,232,1)',
        'rgba(227,116,0,1)',
        'rgba(24,128,56,1)',
        'rgba(217,48,37,1)',
        'rgba(147,52,230,1)',
        'rgba(0,151,167,1)'
      ]
    }
  },
  computed: {
    canSubmit() {
      return this.companiesText.trim() && this.year.toString().trim()
    }
  },
  methods: {
    // H5: 触发隐藏的file input
    triggerUpload: function() {
      this.$refs.fileInput.click()
    },

    // H5: 文件选择回调
    onFileChange: function(e) {
      var file = e.target.files[0]
      if (!file) return
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        uni.showToast({ title: '请选择PDF文件', icon: 'none' })
        return
      }
      this.fileName = file.name
      this.filePath = file
    },

    // App/小程序: 选择PDF文件
    pickFile: function() {
      var self = this
      // #ifdef APP-PLUS
      if (typeof plus !== 'undefined' && plus.android) {
        // 使用 SAF Intent 选择 PDF（与主页相同逻辑）
        var REQUEST_CODE = 20001
        var main = plus.android.runtimeMainActivity()
        var Intent = plus.android.importClass('android.content.Intent')

        var intent = new Intent(Intent.ACTION_OPEN_DOCUMENT)
        intent.addCategory(Intent.CATEGORY_OPENABLE)
        intent.setType('application/pdf')

        // 优先使用系统 DocumentsUI
        try {
          var pm = main.getPackageManager()
          if (plus.android.invoke(pm, 'getPackageInfo', 'com.google.android.documentsui', 0)) {
            intent.setPackage('com.google.android.documentsui')
          }
        } catch(e) {}

        main.onActivityResult = function(requestCode, resultCode, dataIntent) {
          if (requestCode !== REQUEST_CODE) return
          if (resultCode !== -1 || !dataIntent) {
            console.log('[Career Upload] 用户取消选择')
            return
          }
          var uri = dataIntent.getData()
          if (!uri) return
          var uriStr = '' + uri.toString()
          console.log('[Career Upload] URI:', uriStr)

          // 获取原始文件名
          var safFileName = 'upload.pdf'
          try {
            var cr = main.getContentResolver()
            var cursor = plus.android.invoke(cr, 'query', uri, null, null, null, null)
            if (cursor) {
              var moved = plus.android.invoke(cursor, 'moveToFirst')
              if (moved) {
                var colIdx = plus.android.invoke(cursor, 'getColumnIndex', '_display_name')
                if (Number(colIdx) >= 0) {
                  safFileName = '' + plus.android.invoke(cursor, 'getString', colIdx)
                }
              }
              plus.android.invoke(cursor, 'close')
            }
          } catch(e) {}

          self.fileName = safFileName
          self.filePath = '__saf_uri__:' + uriStr
          console.log('[Career Upload] 文件名:', safFileName)
        }

        main.startActivityForResult(intent, REQUEST_CODE)
      } else {
        uni.showModal({
          title: '上传PDF',
          content: '当前设备暂不支持直接选择PDF文件。建议使用浏览器(H5)版本上传。',
          showCancel: false
        })
      }
      // #endif
      // #ifdef MP
      wx.chooseMessageFile({
        count: 1,
        type: 'file',
        extension: ['.pdf'],
        success: function(res) {
          var f = res.tempFiles[0]
          self.fileName = f.name
          self.filePath = f.path
        }
      })
      // #endif
    },

    renderMd: function(text) {
      return renderMarkdown(text)
    },

    // 将人格得分JSON转换为HTML表格（直接生成，避免markdown解析问题）
    buildPersonalityMdTable: function(scores, companies) {
      var personalities = ['ISTJ','ISFJ','INFJ','INTJ','ISTP','ISFP','INFP','INTP',
                           'ESTP','ESFP','ENFP','ENTP','ESTJ','ESFJ','ENFJ','ENTJ']
      var html = '<table style="width:100%;border-collapse:collapse;margin:16rpx 0 20rpx;font-size:26rpx;background:#fff;border-radius:12rpx;overflow:hidden;border:1rpx solid #e0e0e0;">'
      
      // 表头
      html += '<thead><tr style="background:#4d6bfe;">'
      html += '<th style="border:1rpx solid #c5d7f6;padding:14rpx 18rpx;color:#fff;font-weight:600;text-align:center;font-size:26rpx;">人格类型</th>'
      for (var ci = 0; ci < companies.length; ci++) {
        html += '<th style="border:1rpx solid #c5d7f6;padding:14rpx 18rpx;color:#fff;font-weight:600;text-align:center;font-size:26rpx;">' + companies[ci] + '</th>'
      }
      html += '</tr></thead>'
      
      // 数据行
      html += '<tbody>'
      for (var pi = 0; pi < personalities.length; pi++) {
        var p = personalities[pi]
        var sc = scores[p] || {}
        var bgColor = pi % 2 === 0 ? '#f8f9ff' : '#ffffff'
        html += '<tr style="background:' + bgColor + ';">'
        html += '<td style="border:1rpx solid #eee;padding:14rpx 18rpx;text-align:center;color:#333;font-weight:600;font-size:26rpx;">' + p + '</td>'
        for (var ci2 = 0; ci2 < companies.length; ci2++) {
          var val = sc[companies[ci2]]
          if (val === undefined || val === null) val = '-'
          html += '<td style="border:1rpx solid #eee;padding:14rpx 18rpx;text-align:center;color:#4d6bfe;font-weight:bold;font-size:26rpx;">' + val + '</td>'
        }
        html += '</tr>'
      }
      html += '</tbody></table>'
      return html
    },

    doAnalyze: function() {
      var self = this
      if (!self.canSubmit || self.loading) return

      self.loading = true
      self.result = ''
      self.error = ''
      self.personalityScores = null
      self.personalityTableRows = []
      self.resultPart1 = ''
      self.resultPart2 = ''

      var companies = self.companiesText.split(/[,，]/).map(function(s) { return s.trim() }).filter(Boolean)
      self.companies = companies

      uni.showLoading({ title: '分析中...' })

      uni.request({
        url: BASE_URL + '/api/career_analysis',
        method: 'POST',
        data: { companies: companies, year: self.year },
        header: { 'Content-Type': 'application/json' },
        timeout: 180000,
        success: function(res) {
          uni.hideLoading()
          if (res.statusCode === 200 && res.data) {
            var data = res.data
            if (data.error) {
              self.error = data.error
            } else if (data.career_analysis) {
              var rawText = data.career_analysis

              self.resultPart1 = ''
              self.resultPart2 = ''
              self.personalityTableRows = []

              // 如果有人格得分数据，在"第三部分"位置插入表格
              if (data.personality_scores) {
                self.personalityScores = data.personality_scores
                // 按"第三部分"或"16种人格"分割文本
                var splitIdx = -1
                var patterns = ['第三部分', '16种人格', '16种MBTI']
                for (var si = 0; si < patterns.length; si++) {
                  var idx = rawText.indexOf(patterns[si])
                  if (idx >= 0) { splitIdx = idx; break }
                }

                if (splitIdx >= 0) {
                  // 找到标题所在行的结尾
                  var lineEnd = rawText.indexOf('\n', splitIdx)
                  self.resultPart1 = renderMarkdown(rawText.substring(0, lineEnd >= 0 ? lineEnd : rawText.length))
                  // 构建表格行数据
                  var personalities = ['ISTJ','ISFJ','INFJ','INTJ','ISTP','ISFP','INFP','INTP',
                                       'ESTP','ESFP','ENFP','ENTP','ESTJ','ESFJ','ENFJ','ENTJ']
                  var rows = []
                  for (var pi = 0; pi < personalities.length; pi++) {
                    rows.push({ type: personalities[pi], scores: data.personality_scores[personalities[pi]] || {} })
                  }
                  self.personalityTableRows = rows
                  // 第三部分之后的内容
                  var afterContent = lineEnd >= 0 ? rawText.substring(lineEnd) : ''
                  if (afterContent.trim()) {
                    self.resultPart2 = renderMarkdown(afterContent)
                  }
                } else {
                  // 没找到第三部分，表格放末尾
                  self.resultPart1 = renderMarkdown(rawText)
                  var pList = ['ISTJ','ISFJ','INFJ','INTJ','ISTP','ISFP','INFP','INTP',
                               'ESTP','ESFP','ENFP','ENTP','ESTJ','ESFJ','ENFJ','ENTJ']
                  var tRows = []
                  for (var ti = 0; ti < pList.length; ti++) {
                    tRows.push({ type: pList[ti], scores: data.personality_scores[pList[ti]] || {} })
                  }
                  self.personalityTableRows = tRows
                }
                // 绘制柱状图
                setTimeout(function() { self.drawBarChart(data) }, 600)
              } else {
                // 没有人格得分，正常渲染全部内容
                self.resultPart1 = renderMarkdown(rawText)
              }
            } else if (data.result) {
              self.result = renderMarkdown(data.result)
            } else if (data.analysis) {
              self.result = renderMarkdown(data.analysis)
            } else {
              self.error = '未返回有效结果'
            }
          } else {
            self.error = '请求失败 (' + res.statusCode + ')'
          }
        },
        fail: function(err) {
          uni.hideLoading()
          self.error = '网络连接失败，请检查网络或后端服务'
        },
        complete: function() {
          self.loading = false
        }
      })
    },

    drawBarChart: function(data) {
      var self = this
      setTimeout(function() {
        var query = uni.createSelectorQuery().in(self)
        query.select('.bar-canvas').boundingClientRect(function(rect) {
          if (!rect || !rect.width) {
            console.log('barCanvas rect not found, retrying...')
            // 重试一次
            setTimeout(function() { self.drawBarChart(data) }, 500)
            return
          }

          var w = rect.width
          var h = rect.height

          // 使用旧版 Canvas API（兼容所有平台）
          var ctx = uni.createCanvasContext('barCanvas', self)

          var personalities = ['ISTJ','ISFJ','INFJ','INTJ','ISTP','ISFP','INFP','INTP',
                               'ESTP','ESFP','ENFP','ENTP','ESTJ','ESFJ','ENFJ','ENTJ']
          var scores = data.personality_scores || {}
          var companies = self.companies.length > 0 ? self.companies : (data.companies || [])
          var colors = [
            'rgba(26,115,232,1)',
            'rgba(227,116,0,1)',
            'rgba(24,128,56,1)',
            'rgba(217,48,37,1)',
            'rgba(147,52,230,1)',
            'rgba(0,151,167,1)'
          ]
          var colorsLight = [
            'rgba(26,115,232,0.65)',
            'rgba(227,116,0,0.65)',
            'rgba(24,128,56,0.65)',
            'rgba(217,48,37,0.65)',
            'rgba(147,52,230,0.65)',
            'rgba(0,151,167,0.65)'
          ]

          // 检查公司名是否匹配
          if (companies.length > 0 && scores[personalities[0]]) {
            var firstData = scores[personalities[0]]
            var matched = false
            for (var mci = 0; mci < companies.length; mci++) {
              if (firstData[companies[mci]] !== undefined) {
                matched = true
                break
              }
            }
            if (!matched) {
              companies = Object.keys(firstData)
            }
          }

          var pad = { top: h * 0.04, right: w * 0.08, bottom: h * 0.06, left: w * 0.18 }
          var chartW = w - pad.left - pad.right
          var chartH = h - pad.top - pad.bottom

          // 清除画布
          ctx.clearRect(0, 0, w, h)

          // X轴网格线（0-100分，5格）
          var fsGrid = Math.max(8, Math.min(10, w / 45))
          for (var gi = 0; gi <= 5; gi++) {
            var gx = pad.left + (gi / 5) * chartW
            ctx.beginPath()
            ctx.setStrokeStyle(gi === 5 ? '#bdc1c6' : '#e8eaed')
            ctx.setLineWidth(gi === 5 ? 1.2 : 0.6)
            ctx.moveTo(gx, pad.top)
            ctx.lineTo(gx, pad.top + chartH)
            ctx.stroke()

            // X轴刻度标签
            ctx.setFillStyle('#80868b')
            ctx.setFontSize(fsGrid)
            ctx.setTextAlign('center')
            ctx.setTextBaseline('top')
            ctx.fillText(String(gi * 20), gx, pad.top + chartH + 4)
          }

          // 每行高度
          var rowH = chartH / personalities.length
          var barH = Math.max(6, Math.min(14, (rowH - 4) / Math.max(companies.length, 1)))
          var barGap = Math.max(1, barH * 0.15)

          var fsLabel = Math.max(8, Math.min(11, w / 55))

          for (var pi = 0; pi < personalities.length; pi++) {
            var rowY = pad.top + pi * rowH + rowH / 2

            // Y轴标签（人格类型）- 左侧
            ctx.setFillStyle('#5f6368')
            ctx.setFontSize(fsLabel)
            ctx.setTextAlign('right')
            ctx.setTextBaseline('middle')
            ctx.fillText(personalities[pi], pad.left - 6, rowY)

            // 每家公司的水平柱子
            for (var ci = 0; ci < companies.length; ci++) {
              var sc = scores[personalities[pi]] || {}
              var rawVal = sc[companies[ci]]
              var val = parseFloat(rawVal)
              if (isNaN(val)) val = 0
              if (val < 0) val = 0
              if (val > 100) val = 100

              var barW2 = Math.max(0, (val / 100) * chartW)
              var bx = pad.left
              var by = rowY + (ci - (companies.length - 1) / 2) * (barH + barGap) - barH / 2

              // 渐变色（使用线性渐变）
              var grad = ctx.createLinearGradient(bx, by, bx + barW2, by)
              grad.addColorStop(0, colors[ci % colors.length])
              grad.addColorStop(1, colorsLight[ci % colorsLight.length])
              ctx.setFillStyle(grad)

              // 简单矩形（旧API不支持quadraticCurveTo的圆角）
              ctx.fillRect(bx, by, barW2, barH)

              // 分数标签（柱子右侧）
              if (val >= 15) {
                ctx.setFillStyle('#202124')
                ctx.setFontSize(Math.max(7, Math.min(9, w / 50)))
                ctx.setTextAlign('left')
                ctx.setTextBaseline('middle')
                ctx.fillText(String(Math.round(val)), bx + barW2 + 3, by + barH / 2)
              }
            }
          }

          // 图例（放在底部）
          if (companies.length > 0) {
            var legX = pad.left
            var legY = h - pad.bottom + 14

            for (var li = 0; li < companies.length; li++) {
              // 小方块
              ctx.setFillStyle(colors[li % colors.length])
              ctx.fillRect(legX, legY, 13, 11)

              // 文字
              ctx.setFillStyle('#3c4043')
              ctx.setFontSize(Math.max(9, Math.min(11, w / 35)))
              ctx.setTextAlign('left')
              ctx.setTextBaseline('middle')
              ctx.fillText(companies[li], legX + 17, legY + 5.5)

              // 计算下一个图例位置
              var textW = companies[li].length * (w / 45) + 30
              legX += textW + 20
            }
          }

          // 必须调用 draw() 才能渲染
          ctx.draw()
        }).exec()
      }, 500)
    },

    downloadExcel: function() {
      var self = this
      if (!self.personalityScores || !self.companies.length) {
        uni.showToast({ title: '暂无数据可下载', icon: 'none' })
        return
      }

      uni.showLoading({ title: '生成Excel...' })

      // #ifdef H5
      var xhr = new XMLHttpRequest()
      xhr.open('POST', BASE_URL + '/api/download_career_excel', true)
      xhr.setRequestHeader('Content-Type', 'application/json')
      xhr.responseType = 'blob'
      xhr.onload = function() {
        uni.hideLoading()
        if (xhr.status === 200) {
          var blob = xhr.response
          var url = window.URL.createObjectURL(blob)
          var a = document.createElement('a')
          a.href = url
          a.download = 'career_analysis.xlsx'
          document.body.appendChild(a)
          a.click()
          document.body.removeChild(a)
          window.URL.revokeObjectURL(url)
          uni.showToast({ title: '下载成功', icon: 'success' })
        } else {
          uni.showToast({ title: '下载失败', icon: 'none' })
        }
      }
      xhr.onerror = function() {
        uni.hideLoading()
        uni.showToast({ title: '网络错误', icon: 'none' })
      }
      xhr.send(JSON.stringify({
        companies: self.companies,
        personality_scores: self.personalityScores
      }))
      // #endif

      // #ifdef APP-PLUS
      // App端：先 POST 生成 Excel 获取 token，再用 uni.downloadFile 下载
      uni.request({
        url: BASE_URL + '/api/generate_career_excel',
        method: 'POST',
        data: {
          companies: self.companies,
          personality_scores: self.personalityScores
        },
        header: { 'Content-Type': 'application/json' },
        timeout: 60000,
        success: function(res) {
          if (res.statusCode !== 200 || !res.data || !res.data.download_token) {
            uni.hideLoading()
            var errMsg = (res.data && res.data.error) || '生成失败'
            uni.showToast({ title: errMsg, icon: 'none' })
            return
          }
          // 用 uni.downloadFile 下载
          var downloadUrl = BASE_URL + '/api/download_excel_by_token?token=' + res.data.download_token
          uni.downloadFile({
            url: downloadUrl,
            success: function(downloadRes) {
              uni.hideLoading()
              if (downloadRes.statusCode === 200) {
                uni.openDocument({
                  filePath: downloadRes.tempFilePath,
                  fileType: 'xlsx',
                  showMenu: true,
                  success: function() { uni.showToast({ title: '打开成功', icon: 'success' }) },
                  fail: function(err) {
                    console.error('[Excel] openDocument 失败:', err)
                    uni.showToast({ title: '已下载', icon: 'success' })
                  }
                })
              } else {
                uni.showToast({ title: '下载失败', icon: 'none' })
              }
            },
            fail: function(err) {
              uni.hideLoading()
              console.error('[Excel] downloadFile 失败:', err)
              uni.showToast({ title: '下载失败', icon: 'none' })
            }
          })
        },
        fail: function() {
          uni.hideLoading()
          uni.showToast({ title: '网络错误', icon: 'none' })
        }
      })
      // #endif

      // #ifdef MP-WEIXIN
      uni.request({
        url: BASE_URL + '/api/download_career_excel',
        method: 'POST',
        data: {
          companies: self.companies,
          personality_scores: self.personalityScores
        },
        header: { 'Content-Type': 'application/json' },
        responseType: 'arraybuffer',
        timeout: 60000,
        success: function(res) {
          uni.hideLoading()
          if (res.statusCode === 200 && res.data) {
            var fs = uni.getFileSystemManager()
            var filePath = wx.env.USER_DATA_PATH + '/career_analysis.xlsx'
            fs.writeFile({
              filePath: filePath,
              data: res.data,
              encoding: 'binary',
              success: function() {
                uni.openDocument({
                  filePath: filePath,
                  showMenu: true,
                  success: function() {
                    uni.showToast({ title: '打开成功', icon: 'success' })
                  },
                  fail: function() {
                    uni.showToast({ title: '打开失败', icon: 'none' })
                  }
                })
              },
              fail: function() {
                uni.showToast({ title: '保存失败', icon: 'none' })
              }
            })
          } else {
            uni.showToast({ title: '下载失败', icon: 'none' })
          }
        },
        fail: function() {
          uni.hideLoading()
          uni.showToast({ title: '网络错误', icon: 'none' })
        }
      })
      // #endif
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

  .title {
    font-size: 40rpx;
    font-weight: 700;
    color: #333;
    display: block;
  }

  .subtitle {
    font-size: 26rpx;
    color: #999;
    margin-top: 8rpx;
    display: block;
  }
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

    .label {
      font-size: 28rpx;
      font-weight: 600;
      color: #333;
      display: block;
      margin-bottom: 16rpx;
    }

    .input {
      height: 88rpx;
      background: #f5f6fa;
      border-radius: 12rpx;
      padding: 0 24rpx;
      font-size: 28rpx;
      color: #333;
    }
  }
}

.upload-row {
  display: flex;
  align-items: center;
}

.upload-btn {
  display: flex;
  align-items: center;
  padding: 16rpx 24rpx;
  background: #f0f4ff;
  border: 2rpx dashed #4d6bfe;
  border-radius: 12rpx;
  flex: 1;
}

.upload-icon {
  font-size: 36rpx;
  color: #4d6bfe;
  margin-right: 12rpx;
  font-weight: bold;
}

.upload-text {
  font-size: 26rpx;
  color: #4d6bfe;
}

.submit-btn {
  height: 96rpx;
  border-radius: 48rpx;
  background: #ccc;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 32rpx;

  text {
    font-size: 30rpx;
    color: #fff;
    font-weight: 600;
  }

  &.active {
    background: linear-gradient(135deg, #4d6bfe 0%, #6b85ff 100%);
    &:active { opacity: 0.85; }
  }
}

/* 柱状图 */
.chart-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 32rpx;
  box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.06);
  margin-bottom: 32rpx;

  .chart-title {
    font-size: 30rpx;
    font-weight: 600;
    color: #333;
    display: block;
    margin-bottom: 20rpx;
  }

  .bar-canvas {
    width: 100%;
    height: 720rpx;
    display: block;
  }

  .legend-row {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 24rpx;
    margin-top: 16rpx;

    .legend-item {
      display: flex;
      align-items: center;
      gap: 8rpx;
    }

    .legend-dot {
      width: 18rpx;
      height: 18rpx;
      border-radius: 4rpx;
    }

    .legend-text {
      font-size: 24rpx;
      color: #666;
    }
  }
}

.result-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 32rpx;
  box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.06);

  .result-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20rpx;
  }

  .result-title {
    font-size: 30rpx;
    font-weight: 600;
    color: #4d6bfe;
  }

  .download-btn {
    background: linear-gradient(135deg, #07c160 0%, #10d069 100%);
    border-radius: 24rpx;
    padding: 10rpx 28rpx;
    &:active { opacity: 0.85; }

    text {
      font-size: 24rpx;
      color: #fff;
      font-weight: 600;
    }
  }

  .result-content {
    font-size: 28rpx;
    line-height: 1.8;
    color: #333;
  }

  /* 原生表格（兼容iOS） */
  .native-table-wrap {
    margin-top: 16rpx;

    .table-header-row {
      display: flex;
      background: #4d6bfe;
      border-radius: 8rpx 8rpx 0 0;
    }

    .table-body-scroll {
      border: 1rpx solid #e0e0e0;
      border-top: none;
      border-radius: 0 0 8rpx 8rpx;
    }

    .table-data-row {
      display: flex;
      border-bottom: 1rpx solid #eee;

      &:last-child { border-bottom: none; }
    }

    .table-cell {
      padding: 16rpx 12rpx;
      display: flex;
      align-items: center;
      justify-content: center;

      text { font-size: 24rpx; white-space: nowrap; }
    }

    .th {
      text { color: #fff; font-weight: 600; font-size: 24rpx; }
    }

    .td-type {
      width: 140rpx;
      flex-shrink: 0;
      text { color: #333; font-weight: 600; font-size: 24rpx; }
    }

    .td-score {
      flex: 1;
      min-width: 100rpx;
      text { color: #4d6bfe; font-weight: bold; font-size: 26rpx; }
    }
  }
}

.error-box {
  background: #fef0f0;
  border-radius: 12rpx;
  padding: 24rpx;

  text { font-size: 26rpx; color: #f53f3f; }
}
</style>

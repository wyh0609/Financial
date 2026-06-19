/**
 * Markdown 渲染工具（轻量级，适配移动端）
 */

/**
 * 将 Markdown 文本转为富文本 HTML（用于 rich-text 组件）
 * 仅支持常用语法，保持简洁
 */
export function renderMarkdown(text) {
  if (!text) return ''
  
  // ===== 第一步：移除人格得分JSON（必须在代码块提取之前） =====
  // 匹配 ```xxx\nPERSONALITY_SCORES_JSON_START ... PERSONALITY_SCORES_JSON_END\n```
  text = text.replace(/```\w*\n?PERSONALITY_SCORES_JSON_START[\s\S]*?PERSONALITY_SCORES_JSON_END\n?```/gi, '')
  // 匹配无代码块包裹的标记
  text = text.replace(/PERSONALITY_SCORES_JSON_START[\s\S]*?PERSONALITY_SCORES_JSON_END/gi, '')
  // 匹配残留的裸JSON对象
  text = text.replace(/\{[^{}]*"ISTJ"[\s\S]*?\}/gi, '')
  // 清理多余空行
  text = text.replace(/\n{3,}/g, '\n\n')

  // 提取代码块，防止内部被表格等规则干扰
  var codeBlocks = []
  var html = text.replace(/```(\w*)\n?([\s\S]*?)```/g, function(m, lang, code) {
    var idx = codeBlocks.length
    codeBlocks.push('<pre style="background:#1e1e2e;color:#e0e0e0;padding:16rpx;border-radius:12rpx;font-size:24rpx;overflow-x:auto;margin:16rpx 0;white-space:pre-wrap;word-break:break-all;"><code>' + code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</code></pre>')
    return '%%CODEBLOCK_' + idx + '%%'
  })

  // 提取表格块（在转义之前处理，避免 | 被破坏）
  // 支持行首有空白字符的情况
  var tableBlocks = []
  html = html.replace(/^\s*(\|.+\|)\s*\n\s*(\|[-:| ]+\|)\s*\n((?:\s*\|.+\|\s*\n?)*)/gm, function(match, headerLine, sepLine, bodyLines) {
    var idx = tableBlocks.length
    
    // 解析表头
    var headers = headerLine.split('|').filter(function(c) { return c.trim() !== '' })
    // 解析对齐方式
    var aligns = sepLine.split('|').filter(function(c) { return c.trim() !== '' }).map(function(c) {
      c = c.trim()
      if (c.indexOf(':') === 0 && c.indexOf(':', 1) > 0) return 'center'
      if (c.indexOf(':') === 0) return 'left'
      if (c.indexOf(':', c.length - 1) >= 0) return 'right'
      return 'left'
    })
    // 解析数据行
    var rows = bodyLines.trim().split('\n').filter(function(r) { return r.trim() !== '' })
    
    var tableHtml = '<table style="width:100%;border-collapse:collapse;margin:16rpx 0 20rpx;font-size:26rpx;background:#fff;border-radius:12rpx;overflow:hidden;border:1rpx solid #e0e0e0;">'
    
    // 表头
    tableHtml += '<thead><tr style="background:#4d6bfe;">'
    for (var hi = 0; hi < headers.length; hi++) {
      var align = aligns[hi] || 'left'
      tableHtml += '<th style="border:1rpx solid #c5d7f6;padding:14rpx 18rpx;color:#fff;font-weight:600;text-align:' + align + ';font-size:26rpx;">' + headers[hi].trim() + '</th>'
    }
    tableHtml += '</tr></thead>'
    
    // 数据行
    tableHtml += '<tbody>'
    for (var ri = 0; ri < rows.length; ri++) {
      var cells = rows[ri].split('|').filter(function(c) { return c.trim() !== '' })
      var bgColor = ri % 2 === 0 ? '#f8f9ff' : '#ffffff'
      tableHtml += '<tr style="background:' + bgColor + ';">'
      for (var ci = 0; ci < cells.length; ci++) {
        var calign = aligns[ci] || 'left'
        tableHtml += '<td style="border:1rpx solid #eee;padding:14rpx 18rpx;text-align:' + calign + ';color:#333;font-size:26rpx;line-height:1.6;">' + cells[ci].trim() + '</td>'
      }
      tableHtml += '</tr>'
    }
    tableHtml += '</tbody></table>'
    
    tableBlocks.push(tableHtml)
    return '\n%%TABLEBLOCK_' + idx + '%%\n'
  })

  // 转义 HTML 特殊字符
  html = html
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // 行内代码 `code`
  html = html.replace(/`([^`]+)`/g, '<code style="background:#f1f3f5;padding:2rpx 8rpx;border-radius:6rpx;font-size:24rpx;">$1</code>')

  // 标题 ## ~ ####
  html = html
    .replace(/^#### (.+)$/gm, '<h4 style="font-size:28rpx;font-weight:600;color:#666;margin:20rpx 0 10rpx;">$1</h4>')
    .replace(/^### (.+)$/gm, '<h3 style="font-size:30rpx;font-weight:600;color:#4d6bfe;margin:20rpx 0 10rpx;">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 style="font-size:34rpx;font-weight:600;color:#1d2129;margin:20rpx 0 10rpx;">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 style="font-size:40rpx;font-weight:700;color:#1d2129;margin:24rpx 0 12rpx;">$1</h1>')

  // 加粗 **text**
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong style="font-weight:600;color:#1d2129;">$1</strong>')

  // 斜体 *text*
  html = html.replace(/\*([^*]+)\*/g, '<em style="font-style:italic;color:#666;">$1</em>')

  // 引用 > text
  html = html.replace(/^&gt; (.+)$/gm, '<blockquote style="border-left:6rpx solid #4d6bfe;margin:12rpx 0;padding:8rpx 20rpx;color:#666;background:#f8f9ff;border-radius:0 12rpx 12rpx 0;">$1</blockquote>')

  // 无序列表 - item
  html = html.replace(/^- (.+)$/gm, '<li style="margin:6rpx 0;padding-left:16rpx;">• $1</li>')

  // 有序列表 1. item
  html = html.replace(/^\d+\. (.+)$/gm, '<li style="margin:6rpx 0;padding-left:16rpx;">$1</li>')

  // 分割线 ---
  html = html.replace(/^---$/gm, '<hr style="border:none;border-top:2rpx solid #eee;margin:20rpx 0;"/>')

  // 换行
  html = html.replace(/\n/g, '<br/>')

  // 还原代码块
  for (var i = 0; i < codeBlocks.length; i++) {
    html = html.replace('%%CODEBLOCK_' + i + '%%', codeBlocks[i])
  }

  // 还原表格块
  for (var j = 0; j < tableBlocks.length; j++) {
    html = html.replace('%%TABLEBLOCK_' + j + '%%', tableBlocks[j])
  }

  return html
}

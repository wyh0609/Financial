import { marked } from 'marked'

marked.setOptions({
  breaks: true,
  gfm: true,
})

export function renderMd(text) {
  if (!text) return ''
  return marked.parse(text)
}

export function getScoreColor(val) {
  if (val === undefined || val === null) return '#80868b'
  if (val >= 80) return '#1a73e8'
  if (val >= 60) return '#188038'
  if (val >= 40) return '#e37400'
  return '#d93025'
}

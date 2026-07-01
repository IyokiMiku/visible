import katex from 'katex'
import 'katex/dist/katex.min.css'

// 转义 HTML，防止题干文本里的 < > & 破坏 v-html。
function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function renderOne(tex: string): string {
  try {
    return katex.renderToString(tex, { throwOnError: false, displayMode: false })
  } catch {
    return escapeHtml(tex)
  }
}

// 把内联数学标记（$...$ / \(...\) / {{math:...}}）渲染为 KaTeX，其余文本转义。
// 用于 v-html 展示题干/选项/解析里的公式源码。
export function renderMath(text: string): string {
  const src = String(text ?? '')
  if (!src) return ''
  // 统一提取三类标记；用占位切分，保持顺序。
  const pattern = /\$([^$]+)\$|\\\(([\s\S]+?)\\\)|\{\{math:([\s\S]+?)\}\}/g
  let out = ''
  let last = 0
  let m: RegExpExecArray | null
  while ((m = pattern.exec(src)) !== null) {
    out += escapeHtml(src.slice(last, m.index))
    const tex = m[1] ?? m[2] ?? m[3] ?? ''
    out += renderOne(tex)
    last = m.index + m[0].length
  }
  out += escapeHtml(src.slice(last))
  return out.replace(/\n/g, '<br/>')
}

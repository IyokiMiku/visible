window.slideDataMap.set(12, `
  <div class="w-[1440px] h-[810px] bg-white p-[60px] slide-bg">
    <div class="mb-4"><div class="inline-block bg-cyan-100 text-cyan-700 text-xs px-3 py-1 rounded-full mb-4">资料处理</div></div>
    <h2 class="text-[44px] font-bold text-slate-900 mb-3">三套 OCR 各管一摊</h2>
    <p class="text-xl text-slate-500 mb-10">教材和真题大多是扫描版 PDF，文本层要么没有要么是乱码，必须靠 OCR 兜底</p>
    <div class="grid grid-cols-3 gap-7 mb-8">
      <div class="bg-gradient-to-b from-blue-50 to-white rounded-2xl p-7 border-2 border-blue-200">
        <div class="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center mb-4">
          <span class="text-white font-black text-2xl">R</span>
        </div>
        <h3 class="text-xl font-bold text-slate-900 mb-1">RapidOCR</h3>
        <p class="text-slate-400 text-sm mb-4">标准图片型 PDF</p>
        <div class="bg-blue-50 rounded-xl p-3 space-y-1.5">
          <p class="text-blue-700 text-xs">▸ ocr_pdf.py 主引擎</p>
          <p class="text-blue-700 text-xs">▸ 输出 txt / json / md</p>
          <p class="text-blue-700 text-xs">▸ 不依赖外部语言包</p>
        </div>
      </div>
      <div class="bg-gradient-to-b from-emerald-50 to-white rounded-2xl p-7 border-2 border-emerald-200">
        <div class="w-16 h-16 bg-emerald-600 rounded-2xl flex items-center justify-center mb-4">
          <span class="text-white font-black text-2xl">T</span>
        </div>
        <h3 class="text-xl font-bold text-slate-900 mb-1">Tesseract</h3>
        <p class="text-slate-400 text-sm mb-4">教材目录结构化扫描</p>
        <div class="bg-emerald-50 rounded-xl p-3 space-y-1.5">
          <p class="text-emerald-700 text-xs">▸ textbook_toc_scanner.py</p>
          <p class="text-emerald-700 text-xs">▸ 目录检测 + 层级解析</p>
          <p class="text-emerald-700 text-xs">▸ 输出 structured JSON</p>
        </div>
      </div>
      <div class="bg-gradient-to-b from-purple-50 to-white rounded-2xl p-7 border-2 border-purple-200">
        <div class="w-16 h-16 bg-purple-600 rounded-2xl flex items-center justify-center mb-4">
          <span class="text-white font-black text-2xl">P</span>
        </div>
        <h3 class="text-xl font-bold text-slate-900 mb-1">PyMuPDF + Tesseract</h3>
        <p class="text-slate-400 text-sm mb-4">真题 OCR 兜底</p>
        <div class="bg-purple-50 rounded-xl p-3 space-y-1.5">
          <p class="text-purple-700 text-xs">▸ extract_exam_style.py</p>
          <p class="text-purple-700 text-xs">▸ --ocr-pdf 自动启用</p>
          <p class="text-purple-700 text-xs">▸ 高清渲染 + 二值化增强</p>
        </div>
      </div>
    </div>
    <div class="bg-slate-50 rounded-2xl p-6 border border-slate-200">
      <div class="grid grid-cols-3 gap-6">
        <div class="text-center"><p class="text-2xl font-black text-blue-600">自动缓存</p><p class="text-slate-500 text-sm mt-1">OCR 结果落盘，避免重复处理</p></div>
        <div class="text-center border-x border-slate-200"><p class="text-2xl font-black text-emerald-600">目录页检测</p><p class="text-slate-500 text-sm mt-1">关键词 + 结构 + 反向惩罚打分</p></div>
        <div class="text-center"><p class="text-2xl font-black text-purple-600">三套互补</p><p class="text-slate-500 text-sm mt-1">文字型 / 扫描型 / 混合型 PDF 都覆盖</p></div>
      </div>
    </div>
  </div>
`);

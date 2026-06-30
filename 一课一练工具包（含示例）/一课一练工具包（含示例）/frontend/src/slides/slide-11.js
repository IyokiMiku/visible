window.slideDataMap.set(11, `
  <div class="w-[1440px] h-[810px] bg-white p-[60px] slide-bg">
    <div class="mb-4"><div class="inline-block bg-indigo-100 text-indigo-700 text-xs px-3 py-1 rounded-full mb-4">技术架构</div></div>
    <h2 class="text-[44px] font-bold text-slate-900 mb-10">生成器拆成 10 个独立模块</h2>
    <div class="bg-slate-900 rounded-2xl p-5 text-center mb-8">
      <p class="text-white text-2xl font-bold">create.py <span class="text-slate-400 text-lg font-normal">— 主入口，调度以下 10 个模块</span></p>
    </div>
    <div class="grid grid-cols-2 gap-7 mb-7">
      <div class="bg-blue-50 rounded-2xl p-6 border border-blue-100">
        <h3 class="text-base font-bold text-blue-900 mb-4">配置与规划层</h3>
        <div class="space-y-3">
          <div class="bg-blue-600 rounded-lg px-4 py-3"><p class="text-white font-bold text-sm">config_io.py<span class="text-blue-200 text-xs ml-2">配置 · API 调用 · 用量统计</span></p></div>
          <div class="bg-blue-600 rounded-lg px-4 py-3"><p class="text-white font-bold text-sm">planning.py<span class="text-blue-200 text-xs ml-2">解析规划表 · 确定输出路径</span></p></div>
          <div class="bg-blue-300/50 rounded-lg px-4 py-3 border border-blue-400"><p class="text-blue-900 font-semibold text-sm">references.py（加载教材、真题风格、题型定义、编写规范）</p></div>
        </div>
      </div>
      <div class="bg-purple-50 rounded-2xl p-6 border border-purple-100">
        <h3 class="text-base font-bold text-purple-900 mb-4">生成与处理层</h3>
        <div class="space-y-3">
          <div class="bg-purple-600 rounded-lg px-4 py-3"><p class="text-white font-bold text-sm">prompts.py<span class="text-purple-200 text-xs ml-2">构建生成提示词</span></p></div>
          <div class="bg-purple-600 rounded-lg px-4 py-3"><p class="text-white font-bold text-sm">text_generation.py<span class="text-purple-200 text-xs ml-2">生成 + 清洗</span></p></div>
          <div class="bg-purple-300/50 rounded-lg px-4 py-3 border border-purple-400"><p class="text-purple-900 font-semibold text-sm">text_processing.py（文本清理 · 格式标准化）</p></div>
        </div>
      </div>
    </div>
    <div class="bg-emerald-50 rounded-2xl p-6 border border-emerald-200">
      <h3 class="text-base font-bold text-emerald-900 mb-4">质检与交付层</h3>
      <div class="flex gap-3">
        <div class="flex-1 bg-emerald-600 rounded-lg px-3 py-3 text-center"><p class="text-white font-bold text-sm">quality.py</p><p class="text-emerald-200 text-xs mt-1">六项质检 + 定向修复</p></div>
        <div class="flex-1 bg-emerald-600 rounded-lg px-3 py-3 text-center"><p class="text-white font-bold text-sm">docx_generation.py</p><p class="text-emerald-200 text-xs mt-1">Word 文档生成</p></div>
        <div class="flex-1 bg-emerald-600 rounded-lg px-3 py-3 text-center"><p class="text-white font-bold text-sm">postprocess.py</p><p class="text-emerald-200 text-xs mt-1">原卷版 + zip 打包</p></div>
        <div class="flex-1 bg-emerald-700 rounded-lg px-3 py-3 text-center"><p class="text-white font-bold text-sm">runner.py</p><p class="text-emerald-200 text-xs mt-1">主流程编排</p></div>
      </div>
      <div class="mt-3 bg-emerald-200/50 rounded-lg px-4 py-3 border border-emerald-300">
        <p class="text-emerald-900 text-sm">配套工具：check.py（深度质检）· batch_fix_math_docx.py（批量公式修复）· ocr_pdf.py / extract_exam_style.py（资料预处理）</p>
      </div>
    </div>
  </div>
`);

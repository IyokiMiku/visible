window.slideDataMap.set(9, `
  <div class="w-[1440px] h-[810px] bg-white p-[60px] slide-bg">
    <div class="mb-4"><div class="inline-block bg-amber-100 text-amber-700 text-xs px-3 py-1 rounded-full mb-4">真题风格</div></div>
    <h2 class="text-[44px] font-bold text-slate-900 mb-3">用真题的口吻出题，但不照搬真题内容</h2>
    <p class="text-xl text-slate-500 mb-8">真题只用来蒸馏命题风格，不作为知识依据，也不允许复制题干、选项、情境或数值</p>
    <div class="flex gap-8 mb-6">
      <div class="flex-1 bg-slate-50 rounded-2xl p-7 border border-slate-200">
        <h3 class="text-lg font-bold text-slate-800 mb-5">风格蒸馏流程</h3>
        <div class="flex items-center gap-3 mb-6">
          <div class="bg-blue-600 rounded-xl px-4 py-3 flex-1 text-center"><p class="text-white font-bold text-base">历年真题</p><p class="text-blue-200 text-xs mt-1">PDF 提取 / OCR</p></div>
          <span class="text-slate-300 text-xl">→</span>
          <div class="bg-purple-600 rounded-xl px-4 py-3 flex-1 text-center"><p class="text-white font-bold text-base">按题型汇总</p><p class="text-purple-200 text-xs mt-1">分文件存放</p></div>
          <span class="text-slate-300 text-xl">→</span>
          <div class="bg-emerald-600 rounded-xl px-4 py-3 flex-1 text-center"><p class="text-white font-bold text-base">风格库</p><p class="text-emerald-200 text-xs mt-1">9 个风格文件</p></div>
        </div>
        <div class="flex flex-wrap gap-2">
          <span class="bg-blue-100 text-blue-700 text-xs px-3 py-1 rounded-full">风格总则</span>
          <span class="bg-purple-100 text-purple-700 text-xs px-3 py-1 rounded-full">单选风格</span>
          <span class="bg-emerald-100 text-emerald-700 text-xs px-3 py-1 rounded-full">多选风格</span>
          <span class="bg-amber-100 text-amber-700 text-xs px-3 py-1 rounded-full">判断风格</span>
          <span class="bg-pink-100 text-pink-700 text-xs px-3 py-1 rounded-full">填空风格</span>
          <span class="bg-cyan-100 text-cyan-700 text-xs px-3 py-1 rounded-full">简答风格</span>
          <span class="bg-indigo-100 text-indigo-700 text-xs px-3 py-1 rounded-full">计算风格</span>
          <span class="bg-teal-100 text-teal-700 text-xs px-3 py-1 rounded-full">综合风格</span>
          <span class="bg-slate-100 text-slate-700 text-xs px-3 py-1 rounded-full">代表样题</span>
        </div>
      </div>
      <div class="w-[440px] flex flex-col gap-4">
        <div class="bg-red-50 rounded-2xl p-5 border border-red-200">
          <p class="text-red-600 font-bold text-base mb-2">没有风格引导时</p>
          <p class="text-red-800 text-sm leading-relaxed">AI 自由发挥，设问口吻不稳定、选项结构不统一、解析长短随机。</p>
        </div>
        <div class="bg-emerald-50 rounded-2xl p-5 border border-emerald-200">
          <p class="text-emerald-600 font-bold text-base mb-2">有风格引导时</p>
          <p class="text-emerald-800 text-sm leading-relaxed">设问口吻贴近目标省份真题，选项结构和解析篇幅都比较一致。</p>
        </div>
      </div>
    </div>
    <div class="bg-red-50 rounded-xl p-4 border border-red-200">
      <p class="text-red-700 text-base"><span class="font-bold">安全边界：</span>真题不进入知识依据链路。OCR 出来的真题文本只用来提炼风格，不会被原样塞进出题 prompt。</p>
    </div>
  </div>
`);

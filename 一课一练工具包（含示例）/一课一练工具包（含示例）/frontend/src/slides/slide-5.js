window.slideDataMap.set(5, `
  <div class="w-[1440px] h-[810px] bg-white p-[60px] slide-bg">
    <div class="mb-4">
      <div class="inline-block bg-purple-100 text-purple-700 text-xs px-3 py-1 rounded-full mb-4">核心设计</div>
    </div>
    <h2 class="text-[44px] font-bold text-slate-900 mb-3">AI 只负责出题这一步</h2>
    <p class="text-xl text-slate-500 mb-[44px]">前面六层和后面一层都由规则控制，把风格从知识里拆出来，把质量从生成里独立出来</p>

    <div class="space-y-5">
      <div class="bg-gradient-to-r from-blue-700 to-blue-600 rounded-2xl p-7 flex items-center gap-7">
        <div class="w-20 h-20 bg-white/20 rounded-2xl flex items-center justify-center text-3xl text-white font-black shrink-0">1-2</div>
        <div class="flex-1 flex items-center gap-5">
          <div class="bg-white/10 rounded-xl px-5 py-4 flex-1"><span class="text-white/70 text-xs">第一层</span><p class="text-white text-xl font-bold">教材目录 → 定主题</p></div>
          <span class="text-white/40 text-2xl">→</span>
          <div class="bg-white/10 rounded-xl px-5 py-4 flex-1"><span class="text-white/70 text-xs">第二层</span><p class="text-white text-xl font-bold">考纲 → 定知识边界</p></div>
        </div>
      </div>

      <div class="bg-gradient-to-r from-emerald-700 to-emerald-600 rounded-2xl p-7 flex items-center gap-7">
        <div class="w-20 h-20 bg-white/20 rounded-2xl flex items-center justify-center text-3xl text-white font-black shrink-0">3-4</div>
        <div class="flex-1 flex items-center gap-5">
          <div class="bg-white/10 rounded-xl px-5 py-4 flex-1"><span class="text-white/70 text-xs">第三层</span><p class="text-white text-xl font-bold">规划表 → 定题型题量难度</p></div>
          <span class="text-white/40 text-2xl">→</span>
          <div class="bg-white/10 rounded-xl px-5 py-4 flex-1"><span class="text-white/70 text-xs">第四层</span><p class="text-white text-xl font-bold">编写规范 → 定质量底线</p></div>
        </div>
      </div>

      <div class="bg-gradient-to-r from-purple-700 to-purple-600 rounded-2xl p-7 flex items-center gap-7">
        <div class="w-20 h-20 bg-white/20 rounded-2xl flex items-center justify-center text-3xl text-white font-black shrink-0">5-7</div>
        <div class="flex-1 flex items-center gap-3">
          <div class="bg-white/10 rounded-xl px-4 py-4"><span class="text-white/70 text-xs">第五层</span><p class="text-white text-base font-bold">题型定义 → 考类画像</p></div>
          <span class="text-white/40 text-xl">→</span>
          <div class="bg-white/10 rounded-xl px-4 py-4"><span class="text-white/70 text-xs">第六层</span><p class="text-white text-base font-bold">真题风格 → 设问口吻</p></div>
          <span class="text-white/40 text-xl">→</span>
          <div class="bg-white/10 rounded-xl px-4 py-4"><span class="text-white/70 text-xs">第七层</span><p class="text-white text-base font-bold">质检修复 → 交付质量</p></div>
        </div>
      </div>

      <div class="bg-amber-50 rounded-2xl p-5 border border-amber-200">
        <p class="text-amber-900 text-base leading-relaxed"><span class="font-bold">关键点：</span>每一层都独立可控，层与层之间靠规划表串联。把"题风像不像真题"和"题目对不对"分开管，是这套流程能稳定产出的根本原因。</p>
      </div>
    </div>
  </div>
`);

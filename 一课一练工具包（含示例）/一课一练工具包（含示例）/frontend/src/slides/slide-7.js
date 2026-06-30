window.slideDataMap.set(7, `
  <div class="w-[1440px] h-[810px] bg-white p-[60px] slide-bg">
    <div class="mb-4">
      <div class="inline-block bg-green-100 text-green-700 text-xs px-3 py-1 rounded-full mb-4">核心流程</div>
    </div>
    <h2 class="text-[44px] font-bold text-slate-900 mb-10">从考纲到 Word 的完整链路</h2>

    <div class="flex items-start gap-2 mb-10">
      <div class="flex-1 bg-blue-600 rounded-2xl p-5 text-center">
        <div class="text-white/70 text-xs mb-2">步骤 1</div>
        <p class="text-white text-lg font-bold mb-1">准备资料</p>
        <p class="text-blue-200 text-xs">考纲 + 教材 + 真题<br/>+ 编写规范 + 题型定义</p>
      </div>
      <div class="flex items-center pt-10 text-slate-300 text-2xl">→</div>
      <div class="flex-1 bg-cyan-600 rounded-2xl p-5 text-center">
        <div class="text-white/70 text-xs mb-2">步骤 2</div>
        <p class="text-white text-lg font-bold mb-1">生成规划表</p>
        <p class="text-cyan-200 text-xs">8 列 xlsx<br/>教材目录优先匹配</p>
      </div>
      <div class="flex items-center pt-10 text-slate-300 text-2xl">→</div>
      <div class="flex-1 bg-purple-600 rounded-2xl p-5 text-center">
        <div class="text-white/70 text-xs mb-2">步骤 3</div>
        <p class="text-white text-lg font-bold mb-1">AI 生成试卷</p>
        <p class="text-purple-200 text-xs">读取全部参考资料<br/>构建精确 prompt</p>
      </div>
      <div class="flex items-center pt-10 text-slate-300 text-2xl">→</div>
      <div class="flex-1 bg-emerald-600 rounded-2xl p-5 text-center">
        <div class="text-white/70 text-xs mb-2">步骤 4</div>
        <p class="text-white text-lg font-bold mb-1">质检 + 修复</p>
        <p class="text-emerald-200 text-xs">六项自动检测<br/>定向修复问题</p>
      </div>
      <div class="flex items-center pt-10 text-slate-300 text-2xl">→</div>
      <div class="flex-1 bg-orange-600 rounded-2xl p-5 text-center">
        <div class="text-white/70 text-xs mb-2">步骤 5</div>
        <p class="text-white text-lg font-bold mb-1">Word 交付</p>
        <p class="text-orange-200 text-xs">教师版 + 学生版<br/>+ txt + zip</p>
      </div>
    </div>

    <div class="bg-slate-50 rounded-2xl p-7 border border-slate-200">
      <h3 class="text-xl font-bold text-slate-800 mb-5">几个关键点</h3>
      <div class="grid grid-cols-2 gap-x-8 gap-y-4">
        <div class="flex items-start gap-3"><div class="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center text-white text-xs font-bold shrink-0 mt-0.5">1</div><p class="text-slate-700 text-base">规划表决定每练出什么、出多少、什么难度，是整套流程的总开关</p></div>
        <div class="flex items-start gap-3"><div class="w-7 h-7 bg-cyan-600 rounded-lg flex items-center justify-center text-white text-xs font-bold shrink-0 mt-0.5">2</div><p class="text-slate-700 text-base">生成时把规划表、教材、真题风格、题型定义、编写规范一起喂给 AI</p></div>
        <div class="flex items-start gap-3"><div class="w-7 h-7 bg-purple-600 rounded-lg flex items-center justify-center text-white text-xs font-bold shrink-0 mt-0.5">3</div><p class="text-slate-700 text-base">质检自动跑六项检测，发现答案自暴露、题干重复等问题就定向重出</p></div>
        <div class="flex items-start gap-3"><div class="w-7 h-7 bg-emerald-600 rounded-lg flex items-center justify-center text-white text-xs font-bold shrink-0 mt-0.5">4</div><p class="text-slate-700 text-base">每批最多跑 3 卷，避免 bash 超时导致后续批次整体丢失</p></div>
      </div>
    </div>
  </div>
`);

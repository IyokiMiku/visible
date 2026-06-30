window.slideDataMap.set(8, `
  <div class="w-[1440px] h-[810px] bg-white p-[60px] slide-bg">
    <div class="mb-4"><div class="inline-block bg-blue-100 text-blue-700 text-xs px-3 py-1 rounded-full mb-4">规划表</div></div>
    <h2 class="text-[44px] font-bold text-slate-900 mb-3">规划表是整条产线的开关</h2>
    <p class="text-xl text-slate-500 mb-8">一张 xlsx 决定每练的题型、题量、难度和套数，AI 只是按表执行</p>
    <div class="flex gap-8">
      <div class="flex-1">
        <div class="bg-slate-50 rounded-2xl p-6 border border-slate-200">
          <div class="bg-blue-600 rounded-xl px-4 py-3 mb-5 text-center">
            <p class="text-white font-bold text-sm">8 列结构 · 序号 | 知识点 | 主题 | 级别 | 题型 | 难度 | 套数 | 标号</p>
          </div>
          <div class="space-y-2">
            <div class="bg-blue-50 rounded-lg px-4 py-2.5 flex items-center gap-3 border border-blue-100">
              <span class="text-blue-600 font-bold text-xs w-6">#1</span>
              <span class="text-slate-700 text-xs flex-1">机器组成 → 标准 → 单选+填空+综合 → 80:10:10</span>
            </div>
            <div class="bg-amber-50 rounded-lg px-4 py-2.5 flex items-center gap-3 border border-amber-100">
              <span class="text-amber-600 font-bold text-xs w-6">#2</span>
              <span class="text-slate-700 text-xs flex-1">力学性能(一) → 极重要 → 同上 → 同上</span>
            </div>
            <div class="bg-amber-50 rounded-lg px-4 py-2.5 flex items-center gap-3 border border-amber-100">
              <span class="text-amber-600 font-bold text-xs w-6">#3</span>
              <span class="text-slate-700 text-xs flex-1">力学性能(二) → 极重要 → 同上 → 同上</span>
            </div>
            <div class="bg-blue-50 rounded-lg px-4 py-2.5 flex items-center gap-3 border border-blue-100">
              <span class="text-blue-600 font-bold text-xs w-6">#4</span>
              <span class="text-slate-700 text-xs flex-1">金属力学性能 → 标准 → 同上 → 同上</span>
            </div>
            <div class="bg-blue-50 rounded-lg px-4 py-2.5 flex items-center gap-3 border border-blue-100">
              <span class="text-blue-600 font-bold text-xs w-6">#5</span>
              <span class="text-slate-700 text-xs flex-1">钢铁分类 → 标准 → 同上 → 同上</span>
            </div>
            <div class="text-center text-slate-300 text-xs py-1">......</div>
          </div>
        </div>
      </div>
      <div class="w-[400px] flex flex-col gap-4">
        <div class="bg-blue-600 rounded-2xl p-5 text-white">
          <div class="text-4xl font-black mb-1">教材优先</div>
          <div class="text-base font-bold">有教材目录时</div>
          <div class="text-blue-200 text-xs mt-2 leading-relaxed">先读目录定主题，再去考纲里挑对应知识点写进 B 列；没有教材才退回到只用考纲。</div>
        </div>
        <div class="bg-cyan-600 rounded-2xl p-5 text-white">
          <div class="text-4xl font-black mb-1">一表一书</div>
          <div class="text-base font-bold">多教材必须拆分</div>
          <div class="text-cyan-200 text-xs mt-2 leading-relaxed">每本教材独立一个 xlsx，序号从 1 开始，不允许混在一张表里。</div>
        </div>
        <div class="bg-purple-600 rounded-2xl p-5 text-white">
          <div class="text-4xl font-black mb-1">三级标题</div>
          <div class="text-base font-bold">单元 → 章 → 节</div>
          <div class="text-purple-200 text-xs mt-2 leading-relaxed">从教材目录里抽出三级层级，自动拼成标准化试卷标题。</div>
        </div>
      </div>
    </div>
  </div>
`);

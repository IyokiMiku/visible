(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const e of document.querySelectorAll('link[rel="modulepreload"]'))d(e);new MutationObserver(e=>{for(const l of e)if(l.type==="childList")for(const a of l.addedNodes)a.tagName==="LINK"&&a.rel==="modulepreload"&&d(a)}).observe(document,{childList:!0,subtree:!0});function s(e){const l={};return e.integrity&&(l.integrity=e.integrity),e.referrerPolicy&&(l.referrerPolicy=e.referrerPolicy),e.crossOrigin==="use-credentials"?l.credentials="include":e.crossOrigin==="anonymous"?l.credentials="omit":l.credentials="same-origin",l}function d(e){if(e.ep)return;e.ep=!0;const l=s(e);fetch(e.href,l)}})();class r{constructor(){this.currentIndex=0,this.slides=[],this.totalSlides=0,this.viewport=document.getElementById("ppt-viewport"),this.prevBtn=document.getElementById("prevBtn"),this.nextBtn=document.getElementById("nextBtn"),this.progressBarFill=document.getElementById("progressBarFill"),this.pageIndicator=document.getElementById("pageIndicator"),this.init(),this.initWindowMessage()}init(){this.loadSlides(),this.bindEvents(),this.initializePage(),this.updateUI(),this.updateViewportScale()}initWindowMessage(){window.addEventListener("message",t=>{if(!t.data||typeof t.data!="object")return;const{type:s,data:d}=t.data;s==="childrenstart"?(this.prevBtn.style.visibility="hidden",this.nextBtn.style.visibility="hidden",this.progressBarFill.style.visibility="hidden",this.pageIndicator.style.visibility="hidden"):s==="childrenstop"&&(this.prevBtn.style.visibility="visible",this.nextBtn.style.visibility="visible",this.progressBarFill.style.visibility="visible",this.pageIndicator.style.visibility="visible")})}initializePage(){const t=new URLSearchParams(window.location.search);let s=t.get("page");if(!s){s="1",t.set("page","1");const l=`${window.location.pathname}?${t.toString()}`;window.history.replaceState({},"",l)}const d=parseInt(s,10),e=d-1;if(!isNaN(d)&&e>=0&&e<this.totalSlides)this.slides[0]&&this.slides[0].classList.remove("active"),this.currentIndex=e,this.slides[e]&&this.slides[e].classList.add("active");else{console.warn(`无效的页码参数: ${s}，将显示第 1 页`),t.set("page","1");const l=`${window.location.pathname}?${t.toString()}`;window.history.replaceState({},"",l)}}loadSlides(){if(typeof window.slideDataMap>"u"){console.error("未找到 slideDataMap");return}const t=Array.from(window.slideDataMap.keys()).sort((s,d)=>s-d);if(this.totalSlides=t.length,this.totalSlides===0){console.warn("slideDataMap 为空，没有幻灯片可加载");return}t.forEach((s,d)=>{const e=document.createElement("div");e.className="slide",d===0&&e.classList.add("active");const l=window.slideDataMap.get(s);if(!l||typeof l!="string"){this.totalSlides--,console.error(`未找到页码 ${s} 的内容, 或者页码 ${s} 的内容为空`);return}const a=document.createElement("div");a.innerHTML=l.trim(),e.appendChild(a),this.viewport.appendChild(e),this.slides.push(e)})}bindEvents(){this.prevBtn.addEventListener("click",()=>this.prevSlide()),this.nextBtn.addEventListener("click",()=>this.nextSlide()),document.addEventListener("keydown",s=>{s.key==="ArrowLeft"?this.prevSlide():s.key==="ArrowRight"||s.key===" "?(s.preventDefault(),this.nextSlide()):s.key==="Home"?this.goToSlide(0):s.key==="End"&&this.goToSlide(this.totalSlides-1)});let t=0;this.viewport.addEventListener("touchstart",s=>{t=s.touches[0].clientX}),this.viewport.addEventListener("touchend",s=>{const d=s.changedTouches[0].clientX,e=t-d;Math.abs(e)>50&&(e>0?this.nextSlide():this.prevSlide())}),window.addEventListener("resize",()=>this.updateViewportScale())}prevSlide(){this.currentIndex>0&&this.goToSlide(this.currentIndex-1)}nextSlide(){this.currentIndex<this.totalSlides-1&&this.goToSlide(this.currentIndex+1)}goToSlide(t){t<0||t>=this.totalSlides||(this.slides[this.currentIndex].classList.remove("active"),this.currentIndex=t,this.slides[this.currentIndex].classList.add("active"),this.updateUrlPage(t+1),this.updateUI())}updateUrlPage(t){const s=new URLSearchParams(window.location.search);s.set("page",t.toString());const d=`${window.location.pathname}?${s.toString()}`;window.history.replaceState({},"",d)}updateUI(){if(this.totalSlides===0){this.prevBtn.disabled=!0,this.nextBtn.disabled=!0,this.progressBarFill.style.width="0%",this.pageIndicator.textContent="制作中";return}this.prevBtn.disabled=this.currentIndex===0,this.nextBtn.disabled=this.currentIndex===this.totalSlides-1;const t=(this.currentIndex+1)/this.totalSlides*100;this.progressBarFill.style.width=`${t}%`,this.pageIndicator.textContent=`${this.currentIndex+1} / ${this.totalSlides}`}updateViewportScale(){const e=window.innerWidth-40,l=window.innerHeight-40,a=e/1440,p=l/810,x=Math.min(a,p,1);this.viewport.style.transform=`scale(${x})`,console.log(`窗口: ${window.innerWidth}x${window.innerHeight}, 缩放: ${x.toFixed(3)}`)}}class o{constructor(){this.validRoutes=["/","/index.html"],this.checkRoute()}checkRoute(){const t=window.location.pathname;if(t.includes("404.html"))return;this.validRoutes.some(d=>d==="/"?t==="/"||t==="/index.html":t===d)||(console.warn(`Invalid route detected: ${t}, redirecting to 404`),window.location.href="/404.html")}addRoute(t){this.validRoutes.includes(t)||this.validRoutes.push(t)}isValidRoute(t){return this.validRoutes.includes(t)}}window.addEventListener("DOMContentLoaded",()=>{new o,new r});window.slideDataMap.set(1,`
  <div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden slide-bg">
    <div class="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-blue-600/10 to-transparent"></div>
    <div class="absolute bottom-0 left-0 w-[500px] h-[500px] bg-blue-500/5 rounded-full blur-3xl"></div>
    <div class="relative z-10 max-w-[1100px] px-24 pt-48">
      <div class="flex items-center gap-6 mb-12">
        <div class="w-[3px] h-24 bg-blue-500"></div>
        <div>
          <div class="text-blue-500 text-base font-semibold tracking-[0.3em] mb-4">一课一练 · 项目汇报</div>
          <h1 class="text-[4.5rem] font-bold text-slate-800 leading-tight">一课一练试卷生成工具包</h1>
        </div>
      </div>
      <p class="text-3xl text-slate-500 mb-10 ml-9">AI驱动的高职分类考试试卷批量生产系统</p>
      <div class="flex items-center gap-8 ml-9 text-slate-400 text-lg">
        <div class="flex items-center gap-3">
          <div class="w-3 h-3 bg-blue-500 rounded-full"></div>
          <span>项目汇报</span>
        </div>
        <div class="w-[1px] h-5 bg-slate-300"></div>
        <span>2026年6月</span>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(2,`
  <div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden slide-bg">
    <div class="w-[1350px] h-[720px] mx-auto my-[45px] flex">
      <div class="w-1/3 bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center">
        <div class="text-white text-center">
          <h1 class="text-4xl font-bold mb-3">目录</h1>
          <div class="w-20 h-1 bg-white mx-auto"></div>
        </div>
      </div>
      <div class="flex-1 flex flex-col justify-center px-14">
        <div class="space-y-5">
          <div class="flex items-center gap-5">
            <div class="w-14 h-14 bg-blue-100 flex items-center justify-center">
              <span class="text-xl font-bold text-blue-600">01</span>
            </div>
            <div class="flex-1">
              <h3 class="text-xl font-semibold text-gray-800">项目概览</h3>
            </div>
          </div>
          <div class="flex items-center gap-5">
            <div class="w-14 h-14 bg-blue-100 flex items-center justify-center">
              <span class="text-xl font-bold text-blue-600">02</span>
            </div>
            <div class="flex-1">
              <h3 class="text-xl font-semibold text-gray-800">核心流程</h3>
            </div>
          </div>
          <div class="flex items-center gap-5">
            <div class="w-14 h-14 bg-blue-100 flex items-center justify-center">
              <span class="text-xl font-bold text-blue-600">03</span>
            </div>
            <div class="flex-1">
              <h3 class="text-xl font-semibold text-gray-800">技术架构</h3>
            </div>
          </div>
          <div class="flex items-center gap-5">
            <div class="w-14 h-14 bg-blue-100 flex items-center justify-center">
              <span class="text-xl font-bold text-blue-600">04</span>
            </div>
            <div class="flex-1">
              <h3 class="text-xl font-semibold text-gray-800">成果与展望</h3>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(3,`
  <div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden slide-bg">
    <div class="w-[1350px] h-[720px] mx-auto my-[20px]">
      <div class="bg-white p-9 rounded-lg shadow-lg border-l-4 border-blue-600 mb-8">
        <div class="flex items-center justify-between mb-5">
          <h2 class="text-[40px] font-bold text-slate-800">项目定位与背景</h2>
          <div class="px-5 py-3 bg-blue-100 text-blue-700 rounded font-semibold text-base">我们解决什么问题</div>
        </div>
        <p class="text-slate-700 text-[18px] leading-relaxed mb-4">职业教育分类考试需要大量“一课一练”练习卷。传统人工出题——每人每天最多1-2套，质量参差不齐，无法覆盖多教材、多考类的大规模需求。</p>
        <p class="text-slate-700 text-[18px] leading-relaxed">AI直接出题则面临风格不统一、知识不准、格式混乱的困境。本项目通过分层控制体系，把“出题”拆成可管理的标准化流水线。</p>
      </div>
      <div class="grid grid-cols-3 gap-8">
        <div class="col-span-2 bg-white p-7 rounded-lg shadow">
          <h3 class="text-[22px] font-bold text-slate-800 mb-5 pb-3 border-b-2 border-slate-200">三大痛点</h3>
          <div class="space-y-4">
            <div class="flex items-start gap-4 p-4 bg-slate-50 rounded">
              <div class="w-10 h-10 bg-blue-600 text-white rounded flex items-center justify-center text-[18px] font-bold shrink-0">1</div>
              <div><p class="font-semibold text-slate-800 text-[18px]">人工出题效率低，难规模化</p><p class="text-slate-600 text-base mt-2">每人每天最多1-2套，无法覆盖多教材多考类需求</p></div>
            </div>
            <div class="flex items-start gap-4 p-4 bg-slate-50 rounded">
              <div class="w-10 h-10 bg-blue-600 text-white rounded flex items-center justify-center text-[18px] font-bold shrink-0">2</div>
              <div><p class="font-semibold text-slate-800 text-[18px]">AI出题质量不可控</p><p class="text-slate-600 text-base mt-2">风格不统一、知识点不准、格式不规范</p></div>
            </div>
            <div class="flex items-start gap-4 p-4 bg-slate-50 rounded">
              <div class="w-10 h-10 bg-blue-600 text-white rounded flex items-center justify-center text-[18px] font-bold shrink-0">3</div>
              <div><p class="font-semibold text-slate-800 text-[18px]">跨省跨考类命题差异大</p><p class="text-slate-600 text-base mt-2">不同省份、考类、教材的命题风格各不相同，缺乏系统化管理</p></div>
            </div>
          </div>
        </div>
        <div class="flex flex-col gap-8">
          <div class="bg-gradient-to-br from-blue-700 to-blue-600 text-white p-7 rounded-lg shadow-lg">
            <div class="text-[32px] text-blue-300 mb-3">✦</div>
            <p class="text-base leading-relaxed mb-5">一套分层控制的AI试卷生产系统，让“出题”从手艺活变成标准流水线。</p>
            <div class="border-t border-blue-400 pt-4"><p class="text-[14px] text-blue-200">项目答案</p></div>
          </div>
          <div class="bg-blue-50 p-6 rounded-lg border border-blue-200">
            <p class="text-blue-900 font-semibold text-[14px] mb-3">覆盖现状</p>
            <p class="text-blue-800 text-[14px] mb-2"><span class="font-semibold">省份：</span>重庆市、四川省、内蒙古</p>
            <p class="text-blue-800 text-[14px]"><span class="font-semibold">考类：</span>机械加工、汽车、电气等6类</p>
          </div>
        </div>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(4,`
  <div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden slide-bg">
    <div class="w-[1350px] h-[720px] mx-auto my-[20px]">
      <div class="bg-gradient-to-r from-blue-700 to-blue-600 p-5 rounded-xl mb-6 flex items-center justify-between">
        <div>
          <h1 class="text-[38px] font-bold text-white mb-1">项目规模</h1>
          <p class="text-blue-200 text-base">半年内从0到1，持续扩展中</p>
        </div>
        <div class="text-right">
          <div class="text-[30px] font-black text-amber-300">3省6考类</div>
          <p class="text-blue-200 text-[14px]">覆盖范围</p>
        </div>
      </div>
      <div class="grid grid-cols-4 gap-5 mb-6">
        <div class="bg-gradient-to-br from-blue-600 to-blue-700 p-5 rounded-xl shadow-xl">
          <div class="flex items-center justify-between mb-3">
            <p class="text-blue-200 text-[14px] font-semibold">覆盖省份</p>
            <div class="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center text-[20px]">🗺</div>
          </div>
          <div class="text-[32px] font-black text-white mb-2">3 个</div>
          <div class="text-blue-200 text-[14px] font-semibold">重庆·四川·内蒙古</div>
        </div>
        <div class="bg-gradient-to-br from-emerald-600 to-green-700 p-5 rounded-xl shadow-xl">
          <div class="flex items-center justify-between mb-3">
            <p class="text-emerald-200 text-[14px] font-semibold">覆盖考类</p>
            <div class="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center text-[20px]">📚</div>
          </div>
          <div class="text-[32px] font-black text-white mb-2">6 类</div>
          <div class="text-emerald-200 text-[14px] font-semibold">机械·汽车·电气等</div>
        </div>
        <div class="bg-gradient-to-br from-purple-600 to-purple-700 p-5 rounded-xl shadow-xl">
          <div class="flex items-center justify-between mb-3">
            <p class="text-purple-200 text-[14px] font-semibold">生成模块</p>
            <div class="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center text-[20px]">⚙️</div>
          </div>
          <div class="text-[32px] font-black text-white mb-2">10 个</div>
          <div class="text-purple-200 text-[14px] font-semibold">56个Python脚本</div>
        </div>
        <div class="bg-gradient-to-br from-orange-600 to-red-700 p-5 rounded-xl shadow-xl">
          <div class="flex items-center justify-between mb-3">
            <p class="text-orange-200 text-[14px] font-semibold">已产出文档</p>
            <div class="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center text-[20px]">📄</div>
          </div>
          <div class="text-[32px] font-black text-white mb-2">323 份</div>
          <div class="text-orange-200 text-[14px] font-semibold">224文本·133个zip</div>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-5">
        <div class="bg-slate-800 p-5 rounded-xl">
          <h3 class="text-[20px] font-bold text-white mb-4 pb-3 border-b border-slate-700">已产出成果分布</h3>
          <div class="space-y-3">
            <div>
              <div class="flex items-center justify-between mb-2">
                <span class="text-slate-300 text-base">Word文档（解析版+原卷版）</span>
                <span class="text-white font-bold text-[18px]">323</span>
              </div>
              <div class="h-2.5 bg-slate-700 rounded-full overflow-hidden">
                <div class="h-full bg-gradient-to-r from-blue-500 to-cyan-500" style="width: 68%"></div>
              </div>
            </div>
            <div>
              <div class="flex items-center justify-between mb-2">
                <span class="text-slate-300 text-base">原始文本</span>
                <span class="text-white font-bold text-[18px]">224</span>
              </div>
              <div class="h-2.5 bg-slate-700 rounded-full overflow-hidden">
                <div class="h-full bg-gradient-to-r from-emerald-500 to-green-500" style="width: 47%"></div>
              </div>
            </div>
            <div>
              <div class="flex items-center justify-between mb-2">
                <span class="text-slate-300 text-base">Zip打包分发</span>
                <span class="text-white font-bold text-[18px]">133</span>
              </div>
              <div class="h-2.5 bg-slate-700 rounded-full overflow-hidden">
                <div class="h-full bg-gradient-to-r from-purple-500 to-pink-500" style="width: 28%"></div>
              </div>
            </div>
          </div>
        </div>
        <div class="bg-slate-800 p-5 rounded-xl">
          <h3 class="text-[20px] font-bold text-white mb-4 pb-3 border-b border-slate-700">支持的题型与教材</h3>
          <div class="grid grid-cols-2 gap-4">
            <div class="bg-slate-700/50 p-4 rounded-lg">
              <p class="text-slate-400 text-[12px] mb-2">题型覆盖</p>
              <p class="text-[22px] font-black text-white">7+ 种</p>
              <p class="text-slate-400 text-sm">单选·多选·判断·填空·简答·计算·综合</p>
            </div>
            <div class="bg-slate-700/50 p-4 rounded-lg">
              <p class="text-slate-400 text-[12px] mb-2">教材覆盖</p>
              <p class="text-[22px] font-black text-white">9+ 本</p>
              <p class="text-slate-400 text-sm">机械基础·制图·电工电子等</p>
            </div>
            <div class="col-span-2 bg-blue-600/20 border border-blue-500/30 p-4 rounded-lg">
              <div class="flex items-center justify-between">
                <span class="text-blue-300 text-[14px]">规划表驱动·分批控制·质检保障</span>
                <span class="text-[22px] font-black text-blue-400">稳定交付</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(5,`
  <div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden slide-bg">
    <div class="w-[1350px] h-[720px] mx-auto my-[20px] flex flex-col">
      <div class="flex items-center justify-between mb-8 pb-5 border-b-4 border-slate-800">
        <h2 class="text-[38px] font-bold text-slate-800">不只是让AI出题</h2>
        <div class="text-right"><p class="text-base text-slate-500">七层控制体系</p><p class="text-[14px] text-slate-400">分层管控·质量闭环</p></div>
      </div>
      <div class="mb-8">
        <div class="bg-slate-50 p-8 rounded-lg border-l-4 border-slate-800">
          <p class="text-slate-700 text-[18px] leading-relaxed mb-4"><span class="font-bold text-slate-900">核心设计理念：</span>不是简单把考点丢给AI，而是七层递进控制——每一层都有明确的职责边界，共同保证最终试卷质量。</p>
          <p class="text-slate-700 text-[18px] leading-relaxed"><span class="font-bold text-slate-900">优先级原则：</span>教材目录优先定主题 → 考纲定边界 → 规划表是最高控制器 → 真题只迁移风格，不照搬内容。</p>
        </div>
      </div>
      <div class="grid grid-cols-3 gap-8 mb-8">
        <div class="bg-gradient-to-br from-slate-800 to-slate-700 text-white p-6 rounded-lg shadow-lg">
          <div class="text-[30px] font-bold mb-3">01</div>
          <h4 class="text-[20px] font-bold mb-4">主题与边界</h4>
          <ul class="space-y-2 text-base">
            <li class="flex gap-2"><span>▸</span><span>教材目录 → 一课一练主题</span></li>
            <li class="flex gap-2"><span>▸</span><span>考纲 → 知识点边界与要求</span></li>
          </ul>
        </div>
        <div class="bg-gradient-to-br from-blue-600 to-blue-500 text-white p-6 rounded-lg shadow-lg">
          <div class="text-[30px] font-bold mb-3">02</div>
          <h4 class="text-[20px] font-bold mb-4">结构与质量</h4>
          <ul class="space-y-2 text-base">
            <li class="flex gap-2"><span>▸</span><span>规划表 → 题量·题型·难度</span></li>
            <li class="flex gap-2"><span>▸</span><span>编写规范 → 通用质量底线</span></li>
          </ul>
        </div>
        <div class="bg-gradient-to-br from-slate-600 to-slate-500 text-white p-6 rounded-lg shadow-lg">
          <div class="text-[30px] font-bold mb-3">03</div>
          <h4 class="text-[20px] font-bold mb-4">风格与交付</h4>
          <ul class="space-y-2 text-base">
            <li class="flex gap-2"><span>▸</span><span>题型定义JSON → 考类个性化画像</span></li>
            <li class="flex gap-2"><span>▸</span><span>真题风格库 → 设问口吻·解析风格</span></li>
            <li class="flex gap-2"><span>▸</span><span>质检修复 → 最终交付质量</span></li>
          </ul>
        </div>
      </div>
      <div class="flex gap-8">
        <div class="flex-1 border-l-4 border-blue-400 pl-7 bg-blue-50 p-5 rounded">
          <p class="text-slate-700 text-[18px] leading-relaxed mb-2">七层体系的核心：每层独立可控，层与层之间通过规划表串联，形成环环相扣的质量闭环。</p>
          <p class="text-slate-500 text-base">— 设计原则</p>
        </div>
        <div class="w-[420px] bg-amber-50 p-5 rounded border-l-4 border-amber-500">
          <p class="text-amber-900 text-[14px] leading-relaxed"><span class="font-bold">关键洞察：</span>把“风格”从“知识”里拆出来，把“质量”从“生成”里独立出来——这是AI出题从能用变成好用的关键一步。</p>
        </div>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(6,`
  <div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden slide-bg">
    <div class="w-[1350px] h-[720px] mx-auto my-[45px] relative">
      <div class="absolute inset-0 bg-gradient-to-br from-blue-600 to-blue-800" style="clip-path: polygon(0 0, 60% 0, 40% 100%, 0 100%);"></div>
      <div class="absolute inset-0 flex items-center justify-center">
        <div class="text-center">
          <div class="text-white text-7xl font-bold mb-5">02</div>
          <h1 class="text-4xl font-bold text-gray-900 mb-3">核心流程</h1>
          <p class="text-xl text-gray-600">从考纲到试卷的端到端标准化流水线</p>
        </div>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(7,`
  <div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden slide-bg">
    <div class="w-[1350px] h-[720px] mx-auto my-[20px]">
      <div class="flex items-center justify-between mb-8">
        <div>
          <h1 class="text-[38px] font-bold text-slate-900 mb-2">完整生产流程</h1>
          <p class="text-slate-600 text-[18px]">从考纲到试卷的端到端标准化流水线</p>
        </div>
        <div class="bg-blue-600 text-white px-7 py-4 rounded-lg">
          <p class="text-base font-semibold">交付产物</p>
          <p class="text-[28px] font-black">4种格式</p>
        </div>
      </div>
      <div class="space-y-4">
        <div class="flex items-center gap-5">
          <div class="w-[240px] bg-slate-800 text-white p-4 rounded-lg shrink-0">
            <p class="font-bold text-[18px] mb-1">1. 准备资料</p>
            <p class="text-[13px] text-slate-300">考纲·教材·真题入库</p>
          </div>
          <div class="flex-1 relative h-12 bg-slate-200 rounded-lg overflow-hidden">
            <div class="absolute left-0 top-0 h-full bg-gradient-to-r from-emerald-500 to-green-600 flex items-center px-5 text-white font-bold text-base" style="width: 20%">资料就绪 ✓</div>
          </div>
        </div>
        <div class="flex items-center gap-5">
          <div class="w-[240px] bg-slate-800 text-white p-4 rounded-lg shrink-0">
            <p class="font-bold text-[18px] mb-1">2. 真题风格库</p>
            <p class="text-[13px] text-slate-300">风格蒸馏·OCR兜底</p>
          </div>
          <div class="flex-1 relative h-12 bg-slate-200 rounded-lg overflow-hidden">
            <div class="absolute left-[20%] top-0 h-full bg-gradient-to-r from-blue-500 to-indigo-600 flex items-center px-5 text-white font-bold text-base" style="width: 15%">风格萃取 ✓</div>
          </div>
        </div>
        <div class="flex items-center gap-5">
          <div class="w-[240px] bg-slate-800 text-white p-4 rounded-lg shrink-0">
            <p class="font-bold text-[18px] mb-1">3. 考点规划表</p>
            <p class="text-[13px] text-slate-300">教材目录·考纲匹配</p>
          </div>
          <div class="flex-1 relative h-12 bg-slate-200 rounded-lg overflow-hidden">
            <div class="absolute left-[33%] top-0 h-full bg-gradient-to-r from-amber-500 to-orange-600 flex items-center px-5 text-white font-bold text-base" style="width: 17%">规划就绪 ✓</div>
          </div>
        </div>
        <div class="flex items-center gap-5">
          <div class="w-[240px] bg-slate-800 text-white p-4 rounded-lg shrink-0">
            <p class="font-bold text-[18px] mb-1">4. AI生成+质检</p>
            <p class="text-[13px] text-slate-300">prompt构建·六维检测</p>
          </div>
          <div class="flex-1 relative h-12 bg-slate-200 rounded-lg overflow-hidden">
            <div class="absolute left-[50%] top-0 h-full bg-gradient-to-r from-purple-500 to-indigo-600 flex items-center px-5 text-white font-bold text-base" style="width: 22%">核心环节</div>
          </div>
        </div>
        <div class="flex items-center gap-5">
          <div class="w-[240px] bg-slate-800 text-white p-4 rounded-lg shrink-0">
            <p class="font-bold text-[18px] mb-1">5. Word交付</p>
            <p class="text-[13px] text-slate-300">解析版·原卷版·zip</p>
          </div>
          <div class="flex-1 relative h-12 bg-slate-200 rounded-lg overflow-hidden">
            <div class="absolute left-[72%] top-0 h-full bg-gradient-to-r from-teal-500 to-cyan-600 flex items-center px-5 text-white font-bold text-base" style="width: 28%">交付完成 ✓</div>
          </div>
        </div>
      </div>
      <div class="mt-8 grid grid-cols-3 gap-6">
        <div class="bg-white p-5 rounded-lg shadow border-t-4 border-blue-600">
          <p class="text-slate-500 text-sm mb-2">输入</p>
          <p class="text-[24px] font-bold text-slate-900">考纲·教材·真题</p>
          <p class="text-slate-600 text-sm mt-1">3类原始资料</p>
        </div>
        <div class="bg-white p-5 rounded-lg shadow border-t-4 border-amber-500">
          <p class="text-slate-500 text-sm mb-2">控制器</p>
          <p class="text-[24px] font-bold text-slate-900">规划表xlsx</p>
          <p class="text-slate-600 text-sm mt-1">8列结构·管全部</p>
        </div>
        <div class="bg-white p-5 rounded-lg shadow border-t-4 border-emerald-500">
          <p class="text-slate-500 text-sm mb-2">输出</p>
          <p class="text-[24px] font-bold text-slate-900">Word+TXT+ZIP</p>
          <p class="text-slate-600 text-sm mt-1">4种格式交付</p>
        </div>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(8,`
  <div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden slide-bg">
    <div class="w-[1350px] h-[720px] mx-auto my-[20px]">
      <div class="text-center mb-4">
        <h1 class="text-[36px] font-bold text-slate-900 mb-1">规划表：试卷的DNA</h1>
        <p class="text-slate-500 text-base">一张xlsx表管住所有试卷的结构、难度和质量</p>
      </div>
      <div class="bg-slate-50 rounded-2xl p-4">
        <table class="w-full">
          <thead>
            <tr class="border-b-2 border-slate-300">
              <th class="text-left p-2 text-slate-700 font-bold text-sm w-[80px]">列</th>
              <th class="text-left p-2 text-slate-700 font-bold text-sm w-[100px]">名称</th>
              <th class="text-left p-2 bg-blue-600 text-white font-bold text-sm rounded-t-xl">规划表设计</th>
              <th class="text-left p-2 text-slate-700 font-bold text-sm">示例</th>
            </tr>
          </thead>
          <tbody>
            <tr class="border-b border-slate-200"><td class="p-2 font-semibold text-slate-800 text-sm">A</td><td class="p-2 text-sm font-semibold">序号</td><td class="p-2 bg-blue-50 text-sm">每本教材内从1开始连续编号；极重要分两行</td><td class="p-2 text-sm text-slate-600">1, 2, 3...</td></tr>
            <tr class="border-b border-slate-200"><td class="p-2 font-semibold text-slate-800 text-sm">B</td><td class="p-2 text-sm font-semibold">考纲知识点</td><td class="p-2 bg-blue-50 text-sm">保留考纲原文，不添加句号</td><td class="p-2 text-sm text-slate-600">掌握圆柱齿轮主要参数及几何尺寸的计算</td></tr>
            <tr class="border-b border-slate-200"><td class="p-2 font-semibold text-slate-800 text-sm">C</td><td class="p-2 text-sm font-semibold">试卷主题</td><td class="p-2 bg-blue-50 text-sm">去动词、去后缀，≤10字</td><td class="p-2 text-sm text-slate-600">齿轮参数计算</td></tr>
            <tr class="border-b border-slate-200"><td class="p-2 font-semibold text-slate-800 text-sm">D</td><td class="p-2 text-sm font-semibold">级别</td><td class="p-2 bg-blue-50 text-sm">极重要/重要/标准，由认知层次判定</td><td class="p-2 text-sm text-slate-600">极重要</td></tr>
            <tr class="border-b border-slate-200"><td class="p-2 font-semibold text-slate-800 text-sm">E</td><td class="p-2 text-sm font-semibold">题型</td><td class="p-2 bg-blue-50 text-sm">如"单选15+多选9+判断6"</td><td class="p-2 text-sm text-slate-600">单选5+填空3+综合2</td></tr>
            <tr class="border-b border-slate-200"><td class="p-2 font-semibold text-slate-800 text-sm">F</td><td class="p-2 text-sm font-semibold">难度</td><td class="p-2 bg-blue-50 text-sm">"易:中:难"比例</td><td class="p-2 text-sm text-slate-600">80:10:10</td></tr>
            <tr class="border-b border-slate-200"><td class="p-2 font-semibold text-slate-800 text-sm">G</td><td class="p-2 text-sm font-semibold">套数</td><td class="p-2 bg-blue-50 text-sm">固定为1</td><td class="p-2 text-sm text-slate-600">1</td></tr>
            <tr class="border-b border-slate-200"><td class="p-2 font-semibold text-slate-800 text-sm">H</td><td class="p-2 text-sm font-semibold">考纲标号</td><td class="p-2 bg-blue-50 text-sm">课程§节(考点序号)</td><td class="p-2 text-sm text-slate-600">课程1§2(2)</td></tr>
          </tbody>
        </table>
      </div>
      <div class="mt-4 grid grid-cols-3 gap-4">
        <div class="bg-gradient-to-br from-blue-600 to-blue-700 text-white p-3 rounded-xl text-center">
          <p class="text-[24px] font-black mb-1">教材目录优先</p>
          <p class="text-[13px] text-blue-100">有教材先读目录定主题，再匹配考纲</p>
        </div>
        <div class="bg-gradient-to-br from-emerald-600 to-green-700 text-white p-3 rounded-xl text-center">
          <p class="text-[24px] font-black mb-1">多教材拆分</p>
          <p class="text-[13px] text-emerald-100">每本教材独立xlsx，序号各自从1起</p>
        </div>
        <div class="bg-gradient-to-br from-purple-600 to-indigo-700 text-white p-3 rounded-xl text-center">
          <p class="text-[24px] font-black mb-1">三级标题体系</p>
          <p class="text-[13px] text-purple-100">单元→章→节，自动生成标准试卷标题</p>
        </div>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(9,`
  <div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden slide-bg">
    <div class="w-[1350px] h-[720px] mx-auto my-[20px]">
      <div class="text-center mb-4">
        <h1 class="text-[36px] font-bold text-slate-900 mb-1">让AI出的题像真题</h1>
        <p class="text-[17px] text-slate-600">真题只用于风格迁移——模仿设问口吻、选项结构、解析风格，不照搬内容</p>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div class="bg-white rounded-2xl shadow-xl overflow-hidden">
          <div class="bg-gradient-to-r from-blue-600 to-indigo-600 p-3 text-white">
            <div class="flex items-center justify-between mb-1">
              <h3 class="text-[18px] font-black">风格库结构</h3>
              <div class="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center text-[20px]">📋</div>
            </div>
            <p class="text-blue-100 text-[12px]">按省份·考类·题型维度组织</p>
          </div>
          <div class="p-3">
            <div class="mb-2">
              <p class="text-slate-500 text-[12px] font-semibold mb-1">9类风格文件</p>
              <p class="text-slate-700 text-[13px] leading-relaxed">风格总则 + 单选·多选·判断·填空·简答·计算·综合 + 代表样题</p>
            </div>
            <div class="mb-2">
              <p class="text-slate-500 text-[12px] font-semibold mb-1">支持格式</p>
              <p class="text-slate-700 text-[13px] leading-relaxed">文字型PDF直接提取 + 扫描版Tesseract OCR兜底</p>
            </div>
            <div class="grid grid-cols-3 gap-2 pt-2 border-t border-slate-200">
              <div class="text-center"><p class="text-[18px] font-black text-blue-600">7+</p><p class="text-[10px] text-slate-500">题型维度</p></div>
              <div class="text-center"><p class="text-[18px] font-black text-emerald-600">多省</p><p class="text-[10px] text-slate-500">覆盖范围</p></div>
              <div class="text-center"><p class="text-[18px] font-black text-purple-600">txt</p><p class="text-[10px] text-slate-500">存储格式</p></div>
            </div>
          </div>
        </div>
        <div class="bg-white rounded-2xl shadow-xl overflow-hidden">
          <div class="bg-gradient-to-r from-emerald-600 to-green-600 p-3 text-white">
            <div class="flex items-center justify-between mb-1">
              <h3 class="text-[18px] font-black">风格蒸馏流程</h3>
              <div class="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center text-[20px]">🔄</div>
            </div>
            <p class="text-emerald-100 text-[12px]">自动汇总 → 风格提炼 → 按题型拆分</p>
          </div>
          <div class="p-3">
            <div class="mb-2">
              <p class="text-slate-500 text-[12px] font-semibold mb-1">关键技术</p>
              <p class="text-slate-700 text-[13px] leading-relaxed">extract_exam_style.py 支持 --ocr-pdf 对乱码PDF自动启用Tesseract</p>
            </div>
            <div class="mb-2">
              <p class="text-slate-500 text-[12px] font-semibold mb-1">核心原则</p>
              <p class="text-slate-700 text-[13px] leading-relaxed">只迁移风格不等同于简陋；选项结构、解析深度、措辞习惯都要贴近真题</p>
            </div>
            <div class="grid grid-cols-3 gap-2 pt-2 border-t border-slate-200">
              <div class="text-center"><p class="text-[18px] font-black text-emerald-600">OCR</p><p class="text-[10px] text-slate-500">自动兜底</p></div>
              <div class="text-center"><p class="text-[18px] font-black text-blue-600">拆分</p><p class="text-[10px] text-slate-500">按题型</p></div>
              <div class="text-center"><p class="text-[18px] font-black text-purple-600">插件</p><p class="text-[10px] text-slate-500">生成器集成</p></div>
            </div>
          </div>
        </div>
        <div class="bg-white rounded-2xl shadow-xl overflow-hidden">
          <div class="bg-gradient-to-r from-purple-600 to-indigo-600 p-3 text-white">
            <div class="flex items-center justify-between mb-1">
              <h3 class="text-[18px] font-black">效果示例</h3>
              <div class="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center text-[20px]">🎯</div>
            </div>
            <p class="text-purple-100 text-[12px]">重庆市机械加工类·真题风格库</p>
          </div>
          <div class="p-3">
            <div class="mb-2">
              <p class="text-slate-500 text-[12px] font-semibold mb-1">风格特征提取</p>
              <p class="text-slate-700 text-[13px] leading-relaxed">单选4选项、题干带情境、解析简洁直接；判断用√/×、解析一句话说清</p>
            </div>
            <div class="grid grid-cols-3 gap-2 pt-2 border-t border-slate-200">
              <div class="text-center"><p class="text-[18px] font-black text-purple-600">单选</p><p class="text-[10px] text-slate-500">情境化</p></div>
              <div class="text-center"><p class="text-[18px] font-black text-emerald-600">判断</p><p class="text-[10px] text-slate-500">简洁</p></div>
              <div class="text-center"><p class="text-[18px] font-black text-blue-600">综合</p><p class="text-[10px] text-slate-500">递进</p></div>
            </div>
          </div>
        </div>
        <div class="bg-white rounded-2xl shadow-xl overflow-hidden">
          <div class="bg-gradient-to-r from-amber-600 to-orange-600 p-3 text-white">
            <div class="flex items-center justify-between mb-1">
              <h3 class="text-[18px] font-black">安全边界</h3>
              <div class="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center text-[20px]">🛡</div>
            </div>
            <p class="text-amber-100 text-[12px]">风格迁移 ≠ 内容照搬</p>
          </div>
          <div class="p-3">
            <div class="mb-2">
              <p class="text-slate-500 text-[12px] font-semibold mb-1">硬性规则</p>
              <p class="text-slate-700 text-[13px] leading-relaxed">真题不用于知识依据，不得照搬题干、选项、情境或数值</p>
            </div>
            <div class="grid grid-cols-3 gap-2 pt-2 border-t border-slate-200">
              <div class="text-center"><p class="text-[18px] font-black text-amber-600">✓</p><p class="text-[10px] text-slate-500">模仿风格</p></div>
              <div class="text-center"><p class="text-[18px] font-black text-red-500">✗</p><p class="text-[10px] text-slate-500">照搬内容</p></div>
              <div class="text-center"><p class="text-[18px] font-black text-emerald-600">✓</p><p class="text-[10px] text-slate-500">原创情境</p></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(10,`
  <div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden slide-bg">
    <div class="w-[1350px] h-[720px] mx-auto my-[45px] relative">
      <div class="absolute inset-0 bg-gradient-to-br from-blue-600 to-blue-800" style="clip-path: polygon(0 0, 60% 0, 40% 100%, 0 100%);"></div>
      <div class="absolute inset-0 flex items-center justify-center">
        <div class="text-center">
          <div class="text-white text-7xl font-bold mb-5">03</div>
          <h1 class="text-4xl font-bold text-gray-900 mb-3">技术架构</h1>
          <p class="text-xl text-gray-600">模块化设计·多方案OCR·自动化质检</p>
        </div>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(11,`
  <div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden slide-bg">
    <div class="w-[1350px] h-[720px] mx-auto my-[20px]">
      <div class="text-center mb-5">
        <h1 class="text-[36px] font-bold text-slate-900 mb-1">10个核心模块驱动一条生产线</h1>
        <p class="text-slate-600 text-[16px]">生成器模块架构</p>
      </div>
      <div class="grid grid-cols-5 gap-3 h-[600px]">
        <div class="flex flex-col gap-3">
          <div class="bg-blue-100 border-2 border-blue-300 rounded-xl p-4 flex-1">
            <h3 class="font-bold text-blue-900 mb-2 text-sm">主控层</h3>
            <ul class="text-[13px] text-blue-800 space-y-1">
              <li>• runner.py</li>
              <li class="text-xs text-blue-600">流程编排</li>
              <li>• paths.py</li>
              <li class="text-xs text-blue-600">路径常量</li>
            </ul>
          </div>
          <div class="bg-purple-100 border-2 border-purple-300 rounded-xl p-4 flex-1">
            <h3 class="font-bold text-purple-900 mb-2 text-sm">配置与规范</h3>
            <ul class="text-[13px] text-purple-800 space-y-1">
              <li>• config_io.py</li>
              <li class="text-xs text-purple-600">API配置</li>
              <li>• planning.py</li>
              <li class="text-xs text-purple-600">规划表解析</li>
            </ul>
          </div>
        </div>
        <div class="flex flex-col gap-3">
          <div class="bg-gradient-to-br from-blue-600 to-blue-700 border-2 border-blue-800 rounded-xl p-5 flex-1 text-white flex flex-col justify-center">
            <h3 class="font-bold mb-3 text-[18px] text-center">AI生成核心</h3>
            <div class="space-y-2 text-sm">
              <div class="bg-white/20 rounded-lg p-3">
                <p class="font-semibold mb-1">prompts.py</p>
                <p class="text-xs">构建生成提示词</p>
              </div>
              <div class="bg-white/20 rounded-lg p-3">
                <p class="font-semibold mb-1">references.py</p>
                <p class="text-xs">教材·风格加载</p>
              </div>
              <div class="bg-white/20 rounded-lg p-3">
                <p class="font-semibold mb-1">text_generation.py</p>
                <p class="text-xs">生成+清洗</p>
              </div>
            </div>
          </div>
        </div>
        <div class="flex flex-col gap-3">
          <div class="bg-amber-100 border-2 border-amber-300 rounded-xl p-4 flex-1">
            <h3 class="font-bold text-amber-900 mb-2 text-sm">质量保障</h3>
            <ul class="text-[13px] text-amber-800 space-y-1">
              <li>• quality.py</li>
              <li class="text-xs text-amber-600">质检·修复</li>
            </ul>
          </div>
          <div class="bg-cyan-100 border-2 border-cyan-300 rounded-xl p-4 flex-1">
            <h3 class="font-bold text-cyan-900 mb-2 text-sm">文本处理</h3>
            <ul class="text-[13px] text-cyan-800 space-y-1">
              <li>• text_processing.py</li>
              <li class="text-xs text-cyan-600">清洗·拆分</li>
            </ul>
          </div>
        </div>
        <div class="col-span-2 flex flex-col gap-3">
          <div class="flex-[2] flex flex-col gap-3"></div>
          <div class="bg-emerald-100 border-2 border-emerald-300 rounded-xl p-5 flex-1">
            <h3 class="font-bold text-emerald-900 mb-3 text-lg">文档输出</h3>
            <div class="grid grid-cols-2 gap-3">
              <div class="bg-white/60 rounded-lg p-3">
                <p class="text-[13px] text-emerald-700 mb-1">docx_generation.py</p>
                <p class="text-[20px] font-bold text-emerald-900">解析版</p>
                <p class="text-xs text-emerald-600">Word生成</p>
              </div>
              <div class="bg-white/60 rounded-lg p-3">
                <p class="text-[13px] text-emerald-700 mb-1">postprocess.py</p>
                <p class="text-[20px] font-bold text-emerald-900">原卷版</p>
                <p class="text-xs text-emerald-600">后处理·zip</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(12,`
  <div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden slide-bg">
    <div class="w-[1350px] h-[720px] mx-auto my-[30px] flex flex-col">
      <div class="flex items-center justify-between mb-5">
        <div>
          <h1 class="text-3xl font-bold text-gray-800 mb-1">三套OCR方案</h1>
          <p class="text-gray-400 text-sm">PyMuPDF + Tesseract + RapidOCR 应对不同场景</p>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4 flex-1">
        <div class="bg-gray-50 p-5 rounded-lg border-l-4 border-blue-600">
          <div class="flex items-center gap-3 mb-3">
            <div class="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center text-white text-lg font-bold">1</div>
            <div><h2 class="text-lg font-bold text-gray-800">RapidOCR</h2><p class="text-xs text-gray-400">标准图片型PDF</p></div>
          </div>
          <ul class="space-y-2 text-sm text-gray-600">
            <li class="flex items-start gap-2"><span class="w-1.5 h-1.5 rounded-full bg-blue-600 mt-1.5 shrink-0"></span><span>ocr_pdf.py 将图片型PDF转为页面图片+JSON+TXT+Markdown</span></li>
            <li class="flex items-start gap-2"><span class="w-1.5 h-1.5 rounded-full bg-blue-600 mt-1.5 shrink-0"></span><span>PyMuPDF渲染 + RapidOCR识别</span></li>
            <li class="flex items-start gap-2"><span class="w-1.5 h-1.5 rounded-full bg-blue-600 mt-1.5 shrink-0"></span><span>适用场景：整本教材OCR、真题全文提取</span></li>
          </ul>
        </div>
        <div class="bg-gray-50 p-5 rounded-lg border-l-4 border-emerald-600">
          <div class="flex items-center gap-3 mb-3">
            <div class="w-10 h-10 bg-emerald-600 rounded-lg flex items-center justify-center text-white text-lg font-bold">2</div>
            <div><h2 class="text-lg font-bold text-gray-800">Tesseract OCR</h2><p class="text-xs text-gray-400">教材目录结构化扫描</p></div>
          </div>
          <ul class="space-y-2 text-sm text-gray-600">
            <li class="flex items-start gap-2"><span class="w-1.5 h-1.5 rounded-full bg-emerald-600 mt-1.5 shrink-0"></span><span>textbook_toc_scanner.py 目录页检测+层级解析+结构化JSON</span></li>
            <li class="flex items-start gap-2"><span class="w-1.5 h-1.5 rounded-full bg-emerald-600 mt-1.5 shrink-0"></span><span>关键词得分+结构得分+反向惩罚，自动识别目录页码范围</span></li>
            <li class="flex items-start gap-2"><span class="w-1.5 h-1.5 rounded-full bg-emerald-600 mt-1.5 shrink-0"></span><span>输出toc_structured.json供规划表生成器直接读取</span></li>
          </ul>
        </div>
        <div class="bg-gray-50 p-5 rounded-lg border-l-4 border-purple-600">
          <div class="flex items-center gap-3 mb-3">
            <div class="w-10 h-10 bg-purple-600 rounded-lg flex items-center justify-center text-white text-lg font-bold">3</div>
            <div><h2 class="text-lg font-bold text-gray-800">真题风格OCR兜底</h2><p class="text-xs text-gray-400">乱码PDF自动补救</p></div>
          </div>
          <ul class="space-y-2 text-sm text-gray-600">
            <li class="flex items-start gap-2"><span class="w-1.5 h-1.5 rounded-full bg-purple-600 mt-1.5 shrink-0"></span><span>extract_exam_style.py --ocr-pdf 对空文本层或乱码PDF自动启用Tesseract</span></li>
            <li class="flex items-start gap-2"><span class="w-1.5 h-1.5 rounded-full bg-purple-600 mt-1.5 shrink-0"></span><span>支持 --ocr-dpi / --ocr-preprocess 优化识别质量</span></li>
            <li class="flex items-start gap-2"><span class="w-1.5 h-1.5 rounded-full bg-purple-600 mt-1.5 shrink-0"></span><span>生成 _自动汇总样本.txt 避免PDF文本层乱码</span></li>
          </ul>
        </div>
        <div class="bg-gray-50 p-5 rounded-lg border-l-4 border-amber-500">
          <div class="flex items-center gap-3 mb-3">
            <div class="w-10 h-10 bg-amber-500 rounded-lg flex items-center justify-center text-white text-lg font-bold">⚡</div>
            <div><h2 class="text-lg font-bold text-gray-800">缓存与复用</h2><p class="text-xs text-gray-400">避免重复OCR</p></div>
          </div>
          <ul class="space-y-2 text-sm text-gray-600">
            <li class="flex items-start gap-2"><span class="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0"></span><span>OCR结果自动缓存到 03_项目数据/参考资料/教材OCR/ 目录</span></li>
            <li class="flex items-start gap-2"><span class="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0"></span><span>toc_raw.txt 缓存避免重复扫描，--no-reuse-ocr 强制重扫</span></li>
            <li class="flex items-start gap-2"><span class="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0"></span><span>结构化产物供人工校对和后续复用</span></li>
          </ul>
        </div>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(13,`
  <div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden slide-bg">
    <div class="w-[1350px] h-[720px] mx-auto my-[20px]">
      <div class="text-center mb-5">
        <h1 class="text-[36px] font-bold text-slate-900 mb-1">六维质检 + 定向修复</h1>
        <p class="text-slate-600 text-base">生成不是终点，质检修复保证交付质量</p>
      </div>
      <div class="flex flex-col items-center gap-3">
        <div class="bg-gradient-to-r from-slate-800 to-slate-700 text-white p-4 rounded-xl shadow-xl w-[340px] text-center">
          <div class="text-[28px] mb-1">🔍</div>
          <p class="text-[20px] font-bold mb-1">quality.py</p>
          <p class="text-[13px] text-slate-300">质检与修复引擎</p>
        </div>
        <div class="h-6 w-1 bg-slate-300"></div>
        <div class="flex gap-4">
          <div class="bg-blue-50 border-2 border-blue-200 p-3 rounded-lg w-[180px] text-center">
            <p class="font-bold text-blue-900 text-sm mb-1">维度1: 题量</p>
            <p class="text-[11px] text-blue-600">是否与规划表一致</p>
          </div>
          <div class="bg-blue-50 border-2 border-blue-200 p-3 rounded-lg w-[180px] text-center">
            <p class="font-bold text-blue-900 text-sm mb-1">维度2: 自暴露</p>
            <p class="text-[11px] text-blue-600">答案是否在题干中出现</p>
          </div>
          <div class="bg-blue-50 border-2 border-blue-200 p-3 rounded-lg w-[180px] text-center">
            <p class="font-bold text-blue-900 text-sm mb-1">维度3: 选项失衡</p>
            <p class="text-[11px] text-blue-600">选项长度是否明显不均</p>
          </div>
          <div class="bg-blue-50 border-2 border-blue-200 p-3 rounded-lg w-[180px] text-center">
            <p class="font-bold text-blue-900 text-sm mb-1">维度4: 答案分布</p>
            <p class="text-[11px] text-blue-600">是否过度集中在某选项</p>
          </div>
          <div class="bg-blue-50 border-2 border-blue-200 p-3 rounded-lg w-[180px] text-center">
            <p class="font-bold text-blue-900 text-sm mb-1">维度5: 解析质量</p>
            <p class="text-[11px] text-blue-600">是否过短或空泛</p>
          </div>
          <div class="bg-blue-50 border-2 border-blue-200 p-3 rounded-lg w-[180px] text-center">
            <p class="font-bold text-blue-900 text-sm mb-1">维度6: Word格式</p>
            <p class="text-[11px] text-blue-600">公式·答案·解析样式</p>
          </div>
        </div>
      </div>
      <div class="flex gap-4 mt-6">
        <div class="flex-1 space-y-2">
          <div class="h-6 w-1 bg-slate-300 mx-auto"></div>
          <div class="bg-emerald-50 border-2 border-emerald-200 p-3 rounded-lg text-center">
            <p class="font-bold text-emerald-900 text-base mb-1">答案分布自动调整</p>
            <p class="text-[12px] text-emerald-600">检测过度集中→重排选项</p>
          </div>
          <div class="h-6 w-1 bg-slate-300 mx-auto"></div>
          <div class="bg-emerald-50 border-2 border-emerald-200 p-3 rounded-lg text-center">
            <p class="font-bold text-emerald-900 text-base mb-1">公式自动转换</p>
            <p class="text-[12px] text-emerald-600">{math:...} → Word原生公式</p>
          </div>
        </div>
        <div class="flex-1 space-y-2">
          <div class="h-6 w-1 bg-slate-300 mx-auto"></div>
          <div class="bg-emerald-50 border-2 border-emerald-200 p-3 rounded-lg text-center">
            <p class="font-bold text-emerald-900 text-base mb-1">样式批量修复</p>
            <p class="text-[12px] text-emerald-600">答案/解析段落格式统一</p>
          </div>
          <div class="h-6 w-1 bg-slate-300 mx-auto"></div>
          <div class="bg-emerald-50 border-2 border-emerald-200 p-3 rounded-lg text-center">
            <p class="font-bold text-emerald-900 text-base mb-1">AI深度检查</p>
            <p class="text-[12px] text-emerald-600">check.py支持API辅助质检</p>
          </div>
        </div>
      </div>
      <div class="bg-amber-50 border-l-4 border-amber-500 p-3 mt-4 rounded-r-lg">
        <p class="text-amber-900 text-sm"><span class="font-bold">修复能力总览：</span>答案分布重排 · 公式标记→Word公式 · 答案/解析段落格式修复 · 批量batch_fix_math_docx.py · 支持dry-run预览</p>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(14,`
  <div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden slide-bg">
    <div class="w-[1350px] h-[720px] mx-auto my-[45px] relative">
      <div class="absolute inset-0 bg-gradient-to-br from-blue-600 to-blue-800" style="clip-path: polygon(0 0, 60% 0, 40% 100%, 0 100%);"></div>
      <div class="absolute inset-0 flex items-center justify-center">
        <div class="text-center">
          <div class="text-white text-7xl font-bold mb-5">04</div>
          <h1 class="text-4xl font-bold text-gray-900 mb-3">成果与展望</h1>
          <p class="text-xl text-gray-600">已交付成果与未来规划</p>
        </div>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(15,`
  <div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden slide-bg">
    <div class="w-[1350px] h-[720px] mx-auto my-[20px]">
      <div class="text-center mb-4">
        <h1 class="text-[36px] font-bold text-slate-900 mb-1">已覆盖3省6考类，持续扩展中</h1>
        <p class="text-slate-500 text-[17px]">覆盖范围与交付成果一览</p>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div class="space-y-3">
          <div class="bg-gradient-to-br from-blue-600 to-indigo-700 p-4 rounded-2xl shadow-xl">
            <p class="text-blue-200 text-[13px] mb-1 font-semibold">覆盖省份与考类</p>
            <div class="flex items-baseline gap-2 mb-2">
              <span class="text-[32px] font-black text-white">3省</span>
              <span class="text-[18px] text-blue-200">6考类</span>
            </div>
            <div class="text-blue-100 text-sm space-y-1">
              <p>重庆市：机械加工·汽车·电气技术·电子技术·土建</p>
              <p>四川省：汽车类</p>
              <p>内蒙古自治区：机电类</p>
            </div>
          </div>
          <div class="bg-gradient-to-br from-emerald-600 to-green-700 p-4 rounded-2xl shadow-xl">
            <p class="text-emerald-200 text-[13px] mb-1 font-semibold">已产出教材覆盖</p>
            <div class="flex items-baseline gap-2 mb-1">
              <span class="text-[32px] font-black text-white">9+</span>
              <span class="text-[18px] text-emerald-200">本教材</span>
            </div>
            <p class="text-emerald-100 text-sm">机械基础·机械制图·机械加工技术·电工电子·电气测量·电机与电气控制·电子技术·计算机组装与维修·植物保护技术等</p>
          </div>
          <div class="bg-gradient-to-br from-purple-600 to-indigo-700 p-4 rounded-2xl shadow-xl">
            <p class="text-purple-200 text-[13px] mb-1 font-semibold">新增省份扩展流程</p>
            <div class="flex items-baseline gap-2 mb-1">
              <span class="text-[32px] font-black text-white">5步</span>
              <span class="text-[18px] text-purple-200">标准化</span>
            </div>
            <p class="text-purple-100 text-sm">放入考纲PDF → 放入教材PDF → 放入真题 → 生成风格库 → 生成规划表 → 运行create.py</p>
          </div>
        </div>
        <div class="bg-slate-700/50 backdrop-blur rounded-2xl p-4">
          <h2 class="text-[20px] font-bold text-white mb-3 pb-2 border-b border-slate-600">交付物明细</h2>
          <div class="space-y-3">
            <div class="bg-slate-800 rounded-xl p-3">
              <div class="flex items-center justify-between mb-2">
                <h3 class="text-[18px] font-bold text-white">解析版 Word</h3>
                <span class="bg-blue-500 text-white px-2 py-0.5 rounded-full text-xs font-bold">教师用</span>
              </div>
              <div class="text-sm"><p class="text-slate-400 mb-1">包含答案与解析</p><p class="text-blue-400 font-bold text-xl">323 份</p></div>
            </div>
            <div class="bg-slate-800 rounded-xl p-3">
              <div class="flex items-center justify-between mb-2">
                <h3 class="text-[18px] font-bold text-white">原卷版 Word</h3>
                <span class="bg-emerald-500 text-white px-2 py-0.5 rounded-full text-xs font-bold">学生用</span>
              </div>
              <div class="text-sm"><p class="text-slate-400 mb-1">去除答案与解析</p><p class="text-emerald-400 font-bold text-xl">与解析版配对</p></div>
            </div>
            <div class="bg-slate-800 rounded-xl p-3">
              <div class="flex items-center justify-between mb-2">
                <h3 class="text-[18px] font-bold text-white">原始文本 + Zip</h3>
                <span class="bg-purple-500 text-white px-2 py-0.5 rounded-full text-xs font-bold">归档</span>
              </div>
              <div class="text-sm"><p class="text-slate-400 mb-1">TXT可追溯 + ZIP打包分发</p><p class="text-purple-400 font-bold text-xl">224 + 133</p></div>
            </div>
            <div class="bg-gradient-to-r from-emerald-600 to-green-600 rounded-xl p-3">
              <div class="flex items-center justify-between">
                <div><p class="text-emerald-100 text-xs mb-1">累计交付</p><p class="text-[28px] font-black text-white">680+ 文件</p></div>
                <div class="text-right"><p class="text-emerald-100 text-xs mb-1">质检通过</p><p class="text-[24px] font-black text-white">稳定交付</p></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(16,`
  <div class="w-[1440px] h-[810px] slide-bg relative overflow-hidden">
    <div class="flex w-full h-full">
      <div class="w-[576px] bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center">
        <div class="text-white text-center px-6">
          <h1 class="text-5xl font-bold mb-5">谢谢</h1>
          <div class="w-28 h-1 bg-white mx-auto mb-5"></div>
          <p class="text-xl">一课一练试卷生成工具包</p>
          <p class="text-blue-200 mt-3 text-base">AI驱动的高职分类考试试卷批量生产系统</p>
        </div>
      </div>
      <div class="flex-1 flex flex-col justify-center px-12">
        <h2 class="text-3xl font-bold text-gray-900 mb-6">项目概要</h2>
        <div class="space-y-4 text-gray-700 text-base">
          <div class="flex items-start gap-3">
            <div class="w-8 h-8 bg-blue-100 rounded flex items-center justify-center shrink-0 mt-0.5">
              <span class="text-sm">📍</span>
            </div>
            <div>
              <p class="text-sm text-gray-500">覆盖范围</p>
              <p class="font-semibold">3省6考类 · 9+本教材</p>
            </div>
          </div>
          <div class="flex items-start gap-3">
            <div class="w-8 h-8 bg-blue-100 rounded flex items-center justify-center shrink-0 mt-0.5">
              <span class="text-sm">⚙️</span>
            </div>
            <div>
              <p class="text-sm text-gray-500">技术栈</p>
              <p class="font-semibold">Python · 10模块 · 三套OCR方案</p>
            </div>
          </div>
          <div class="flex items-start gap-3">
            <div class="w-8 h-8 bg-blue-100 rounded flex items-center justify-center shrink-0 mt-0.5">
              <span class="text-sm">📦</span>
            </div>
            <div>
              <p class="text-sm text-gray-500">交付成果</p>
              <p class="font-semibold">323 Word · 224 TXT · 133 Zip</p>
            </div>
          </div>
          <div class="flex items-start gap-3">
            <div class="w-8 h-8 bg-blue-100 rounded flex items-center justify-center shrink-0 mt-0.5">
              <span class="text-sm">🔑</span>
            </div>
            <div>
              <p class="text-sm text-gray-500">核心亮点</p>
              <p class="font-semibold">7层控制 · 规划表驱动 · 真题风格蒸馏 · 自动化质检</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
`);

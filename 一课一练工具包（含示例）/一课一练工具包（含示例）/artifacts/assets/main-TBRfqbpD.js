(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const e of document.querySelectorAll('link[rel="modulepreload"]'))d(e);new MutationObserver(e=>{for(const l of e)if(l.type==="childList")for(const a of l.addedNodes)a.tagName==="LINK"&&a.rel==="modulepreload"&&d(a)}).observe(document,{childList:!0,subtree:!0});function s(e){const l={};return e.integrity&&(l.integrity=e.integrity),e.referrerPolicy&&(l.referrerPolicy=e.referrerPolicy),e.crossOrigin==="use-credentials"?l.credentials="include":e.crossOrigin==="anonymous"?l.credentials="omit":l.credentials="same-origin",l}function d(e){if(e.ep)return;e.ep=!0;const l=s(e);fetch(e.href,l)}})();class n{constructor(){this.currentIndex=0,this.slides=[],this.totalSlides=0,this.viewport=document.getElementById("ppt-viewport"),this.prevBtn=document.getElementById("prevBtn"),this.nextBtn=document.getElementById("nextBtn"),this.progressBarFill=document.getElementById("progressBarFill"),this.pageIndicator=document.getElementById("pageIndicator"),this.init(),this.initWindowMessage()}init(){this.loadSlides(),this.bindEvents(),this.initializePage(),this.updateUI(),this.updateViewportScale()}initWindowMessage(){window.addEventListener("message",t=>{if(!t.data||typeof t.data!="object")return;const{type:s,data:d}=t.data;s==="childrenstart"?(this.prevBtn.style.visibility="hidden",this.nextBtn.style.visibility="hidden",this.progressBarFill.style.visibility="hidden",this.pageIndicator.style.visibility="hidden"):s==="childrenstop"&&(this.prevBtn.style.visibility="visible",this.nextBtn.style.visibility="visible",this.progressBarFill.style.visibility="visible",this.pageIndicator.style.visibility="visible")})}initializePage(){const t=new URLSearchParams(window.location.search);let s=t.get("page");if(!s){s="1",t.set("page","1");const l=`${window.location.pathname}?${t.toString()}`;window.history.replaceState({},"",l)}const d=parseInt(s,10),e=d-1;if(!isNaN(d)&&e>=0&&e<this.totalSlides)this.slides[0]&&this.slides[0].classList.remove("active"),this.currentIndex=e,this.slides[e]&&this.slides[e].classList.add("active");else{console.warn(`无效的页码参数: ${s}，将显示第 1 页`),t.set("page","1");const l=`${window.location.pathname}?${t.toString()}`;window.history.replaceState({},"",l)}}loadSlides(){if(typeof window.slideDataMap>"u"){console.error("未找到 slideDataMap");return}const t=Array.from(window.slideDataMap.keys()).sort((s,d)=>s-d);if(this.totalSlides=t.length,this.totalSlides===0){console.warn("slideDataMap 为空，没有幻灯片可加载");return}t.forEach((s,d)=>{const e=document.createElement("div");e.className="slide",d===0&&e.classList.add("active");const l=window.slideDataMap.get(s);if(!l||typeof l!="string"){this.totalSlides--,console.error(`未找到页码 ${s} 的内容, 或者页码 ${s} 的内容为空`);return}const a=document.createElement("div");a.innerHTML=l.trim(),e.appendChild(a),this.viewport.appendChild(e),this.slides.push(e)})}bindEvents(){this.prevBtn.addEventListener("click",()=>this.prevSlide()),this.nextBtn.addEventListener("click",()=>this.nextSlide()),document.addEventListener("keydown",s=>{s.key==="ArrowLeft"?this.prevSlide():s.key==="ArrowRight"||s.key===" "?(s.preventDefault(),this.nextSlide()):s.key==="Home"?this.goToSlide(0):s.key==="End"&&this.goToSlide(this.totalSlides-1)});let t=0;this.viewport.addEventListener("touchstart",s=>{t=s.touches[0].clientX}),this.viewport.addEventListener("touchend",s=>{const d=s.changedTouches[0].clientX,e=t-d;Math.abs(e)>50&&(e>0?this.nextSlide():this.prevSlide())}),window.addEventListener("resize",()=>this.updateViewportScale())}prevSlide(){this.currentIndex>0&&this.goToSlide(this.currentIndex-1)}nextSlide(){this.currentIndex<this.totalSlides-1&&this.goToSlide(this.currentIndex+1)}goToSlide(t){t<0||t>=this.totalSlides||(this.slides[this.currentIndex].classList.remove("active"),this.currentIndex=t,this.slides[this.currentIndex].classList.add("active"),this.updateUrlPage(t+1),this.updateUI())}updateUrlPage(t){const s=new URLSearchParams(window.location.search);s.set("page",t.toString());const d=`${window.location.pathname}?${s.toString()}`;window.history.replaceState({},"",d)}updateUI(){if(this.totalSlides===0){this.prevBtn.disabled=!0,this.nextBtn.disabled=!0,this.progressBarFill.style.width="0%",this.pageIndicator.textContent="制作中";return}this.prevBtn.disabled=this.currentIndex===0,this.nextBtn.disabled=this.currentIndex===this.totalSlides-1;const t=(this.currentIndex+1)/this.totalSlides*100;this.progressBarFill.style.width=`${t}%`,this.pageIndicator.textContent=`${this.currentIndex+1} / ${this.totalSlides}`}updateViewportScale(){const e=window.innerWidth-40,l=window.innerHeight-40,a=e/1440,p=l/810,x=Math.min(a,p,1);this.viewport.style.transform=`scale(${x})`,console.log(`窗口: ${window.innerWidth}x${window.innerHeight}, 缩放: ${x.toFixed(3)}`)}}class r{constructor(){this.validRoutes=["/","/index.html"],this.checkRoute()}checkRoute(){const t=window.location.pathname;if(t.includes("404.html"))return;this.validRoutes.some(d=>d==="/"?t==="/"||t==="/index.html":t===d)||(console.warn(`Invalid route detected: ${t}, redirecting to 404`),window.location.href="/404.html")}addRoute(t){this.validRoutes.includes(t)||this.validRoutes.push(t)}isValidRoute(t){return this.validRoutes.includes(t)}}window.addEventListener("DOMContentLoaded",()=>{new r,new n});window.slideDataMap.set(1,`
  <div class="w-[1440px] h-[810px] bg-slate-900 relative overflow-hidden slide-bg">
    <div class="absolute top-[-100px] right-[-100px] w-[500px] h-[500px] rounded-full bg-blue-600/10 blur-3xl"></div>
    <div class="absolute bottom-[-80px] left-[-80px] w-[360px] h-[360px] rounded-full bg-cyan-600/10 blur-3xl"></div>
    <div class="relative z-10 flex items-center h-full px-28">
      <div>
        <div class="text-blue-400 text-sm tracking-[0.3em] mb-6">项目介绍 · 2026 年 6 月</div>
        <h1 class="text-[4.5rem] font-bold text-white leading-tight mb-4">一课一练<br/>试卷生成工具包</h1>
        <div class="w-16 h-1 bg-blue-500 mb-6"></div>
        <p class="text-2xl text-slate-300 mb-14">面向高职分类考试的试卷批量生产工具</p>
        <div class="flex items-center gap-5 text-slate-400 text-base">
          <span class="px-3 py-1.5 border border-slate-600 rounded-full">覆盖 3 省 6 考类</span>
          <span class="px-3 py-1.5 border border-slate-600 rounded-full">规划表驱动</span>
          <span class="px-3 py-1.5 border border-slate-600 rounded-full">323 套 Word 已产出</span>
        </div>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(2,`
  <div class="w-[1440px] h-[810px] bg-white p-[60px] slide-bg">
    <div class="mb-12">
      <div class="text-blue-600 text-sm tracking-[0.3em] mb-3">CONTENTS</div>
      <h2 class="text-[44px] font-bold text-slate-900">目录</h2>
      <div class="w-12 h-1 bg-blue-500 mt-4"></div>
    </div>
    <div class="grid grid-cols-2 gap-x-16 gap-y-8 max-w-[1100px]">
      <div class="flex items-start gap-6 pb-6 border-b border-slate-200">
        <div class="text-[44px] font-black text-blue-600 leading-none w-16">01</div>
        <div>
          <h3 class="text-2xl font-bold text-slate-900 mb-2">项目概览</h3>
          <p class="text-slate-500 text-base">为什么做这套工具，已经做到什么程度</p>
        </div>
      </div>
      <div class="flex items-start gap-6 pb-6 border-b border-slate-200">
        <div class="text-[44px] font-black text-cyan-600 leading-none w-16">02</div>
        <div>
          <h3 class="text-2xl font-bold text-slate-900 mb-2">核心流程</h3>
          <p class="text-slate-500 text-base">从考纲到 Word 的完整链路、规划表与真题风格</p>
        </div>
      </div>
      <div class="flex items-start gap-6 pb-6 border-b border-slate-200">
        <div class="text-[44px] font-black text-purple-600 leading-none w-16">03</div>
        <div>
          <h3 class="text-2xl font-bold text-slate-900 mb-2">技术架构</h3>
          <p class="text-slate-500 text-base">生成器模块拆分、三套 OCR、六项质检</p>
        </div>
      </div>
      <div class="flex items-start gap-6 pb-6 border-b border-slate-200">
        <div class="text-[44px] font-black text-emerald-600 leading-none w-16">04</div>
        <div>
          <h3 class="text-2xl font-bold text-slate-900 mb-2">成果与展望</h3>
          <p class="text-slate-500 text-base">已覆盖省份考类、扩展流程、后续方向</p>
        </div>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(3,`
  <div class="w-[1440px] h-[810px] bg-white p-[60px] slide-bg">
    <div class="mb-4">
      <div class="inline-block bg-red-100 text-red-700 text-xs px-3 py-1 rounded-full mb-4">项目背景</div>
    </div>
    <h2 class="text-[44px] font-bold text-slate-900 mb-3">为什么需要这个工具</h2>
    <p class="text-xl text-slate-500 mb-[48px]">高职分类考试要的卷子多，纯人工出题跟不上，直接让 AI 出又控制不住质量</p>
    <div class="grid grid-cols-3 gap-8">
      <div class="bg-white rounded-2xl p-8 shadow-sm border border-slate-200">
        <div class="text-5xl font-black text-red-200 mb-3">01</div>
        <h3 class="text-xl font-bold text-slate-900 mb-3">人工出题跟不上量</h3>
        <p class="text-slate-600 text-base leading-relaxed">一名老师一天最多一两套，要同时覆盖多省多考类多本教材时，人力基本撑不住。</p>
      </div>
      <div class="bg-white rounded-2xl p-8 shadow-sm border border-slate-200">
        <div class="text-5xl font-black text-amber-200 mb-3">02</div>
        <h3 class="text-xl font-bold text-slate-900 mb-3">直接让 AI 出质量不稳</h3>
        <p class="text-slate-600 text-base leading-relaxed">题风忽高忽低、知识点有偏差、答案偶尔出现在题干里，没有质检环节很难交付。</p>
      </div>
      <div class="bg-white rounded-2xl p-8 shadow-sm border border-slate-200">
        <div class="text-5xl font-black text-blue-200 mb-3">03</div>
        <h3 class="text-xl font-bold text-slate-900 mb-3">跨省跨考类差异大</h3>
        <p class="text-slate-600 text-base leading-relaxed">每个省每个考类的真题口吻、题型配比、知识侧重都不一样，没有统一流程很容易做散。</p>
      </div>
    </div>
    <div class="mt-8 bg-blue-50 border-l-4 border-blue-600 rounded-r-xl px-6 py-5">
      <p class="text-slate-800 text-lg"><span class="font-bold">我们的做法：</span>把"出题"拆成一条可管理的流水线，AI 只负责中间一步，前后都由规则和质检兜住。</p>
    </div>
  </div>
`);window.slideDataMap.set(4,`
  <div class="w-[1440px] h-[810px] bg-white p-[60px] slide-bg">
    <div class="mb-4"><div class="inline-block bg-slate-200 text-slate-700 text-xs px-3 py-1 rounded-full mb-4">项目规模</div></div>
    <h2 class="text-[44px] font-bold text-slate-900 mb-3">目前实际产出</h2>
    <p class="text-xl text-slate-500 mb-10">从 2025 年底起步，半年时间覆盖了三个省六个考类</p>
    <div class="grid grid-cols-4 gap-6 mb-10">
      <div class="bg-blue-600 rounded-2xl p-7 text-white">
        <div class="text-[56px] font-black leading-none mb-3">3</div>
        <div class="text-lg font-bold">个省份</div>
        <div class="text-blue-200 text-sm mt-2">重庆 · 四川 · 内蒙古</div>
      </div>
      <div class="bg-cyan-600 rounded-2xl p-7 text-white">
        <div class="text-[56px] font-black leading-none mb-3">6</div>
        <div class="text-lg font-bold">个考类</div>
        <div class="text-cyan-200 text-sm mt-2">机械加工 · 汽车等</div>
      </div>
      <div class="bg-purple-600 rounded-2xl p-7 text-white">
        <div class="text-[56px] font-black leading-none mb-3">9+</div>
        <div class="text-lg font-bold">本教材</div>
        <div class="text-purple-200 text-sm mt-2">已生成独立规划表</div>
      </div>
      <div class="bg-emerald-600 rounded-2xl p-7 text-white">
        <div class="text-[56px] font-black leading-none mb-3">323</div>
        <div class="text-lg font-bold">套 Word 试卷</div>
        <div class="text-emerald-200 text-sm mt-2">另含 224 份原始文本</div>
      </div>
    </div>
    <div class="grid grid-cols-2 gap-8">
      <div class="bg-slate-50 rounded-2xl p-7 border border-slate-200">
        <h3 class="text-lg font-bold text-slate-800 mb-5">代码规模</h3>
        <div class="space-y-4">
          <div><div class="flex justify-between mb-2"><span class="text-slate-600">Python 脚本</span><span class="font-bold text-slate-800">56 个</span></div><div class="h-2.5 bg-slate-200 rounded-full overflow-hidden"><div class="h-full bg-blue-600 rounded-full w-[100%]"></div></div></div>
          <div><div class="flex justify-between mb-2"><span class="text-slate-600">生成器核心模块</span><span class="font-bold text-slate-800">10 个</span></div><div class="h-2.5 bg-slate-200 rounded-full overflow-hidden"><div class="h-full bg-cyan-600 rounded-full w-[18%]"></div></div></div>
          <div><div class="flex justify-between mb-2"><span class="text-slate-600">OCR 方案</span><span class="font-bold text-slate-800">3 套</span></div><div class="h-2.5 bg-slate-200 rounded-full overflow-hidden"><div class="h-full bg-purple-600 rounded-full w-[6%]"></div></div></div>
        </div>
      </div>
      <div class="bg-slate-50 rounded-2xl p-7 border border-slate-200">
        <h3 class="text-lg font-bold text-slate-800 mb-5">交付物</h3>
        <div class="space-y-3">
          <div class="flex items-center gap-3 bg-white rounded-xl p-3 border border-slate-100"><div class="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center text-blue-700 font-bold text-sm">W</div><div><p class="font-bold text-slate-800 text-sm">解析版 Word（教师用）</p><p class="text-slate-400 text-xs">含答案与解析</p></div></div>
          <div class="flex items-center gap-3 bg-white rounded-xl p-3 border border-slate-100"><div class="w-10 h-10 bg-cyan-100 rounded-lg flex items-center justify-center text-cyan-700 font-bold text-sm">W</div><div><p class="font-bold text-slate-800 text-sm">原卷版 Word（学生用）</p><p class="text-slate-400 text-xs">去答案与解析</p></div></div>
          <div class="flex items-center gap-3 bg-white rounded-xl p-3 border border-slate-100"><div class="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center text-purple-700 font-bold text-sm">T</div><div><p class="font-bold text-slate-800 text-sm">原始文本 + zip 包</p><p class="text-slate-400 text-xs">便于二次加工</p></div></div>
        </div>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(5,`
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
`);window.slideDataMap.set(6,`
  <div class="w-[1440px] h-[810px] bg-gradient-to-br from-blue-700 to-blue-900 relative overflow-hidden slide-bg">
    <div class="absolute top-[-150px] right-[-100px] w-[500px] h-[500px] rounded-full bg-white/5 blur-3xl"></div>
    <div class="absolute bottom-[-100px] left-[-100px] w-[400px] h-[400px] rounded-full bg-cyan-500/10 blur-3xl"></div>
    <div class="relative z-10 flex items-center h-full px-28">
      <div>
        <div class="text-cyan-300 text-sm tracking-[0.4em] mb-6">PART 02</div>
        <div class="text-white/40 text-7xl font-black mb-4">02</div>
        <h1 class="text-[5rem] font-bold text-white leading-tight mb-6">核心流程</h1>
        <div class="w-20 h-1 bg-cyan-400 mb-8"></div>
        <p class="text-2xl text-slate-300 max-w-[700px] leading-relaxed">从考纲 PDF 到最终 Word 交付的完整链路，以及规划表、真题风格这两个核心机制</p>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(7,`
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
`);window.slideDataMap.set(8,`
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
`);window.slideDataMap.set(9,`
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
`);window.slideDataMap.set(10,`
  <div class="w-[1440px] h-[810px] bg-gradient-to-br from-purple-700 to-purple-900 relative overflow-hidden slide-bg">
    <div class="absolute top-[-150px] left-[-100px] w-[500px] h-[500px] rounded-full bg-white/5 blur-3xl"></div>
    <div class="absolute bottom-[-100px] right-[-100px] w-[400px] h-[400px] rounded-full bg-pink-500/10 blur-3xl"></div>
    <div class="relative z-10 flex items-center h-full px-28">
      <div>
        <div class="text-pink-300 text-sm tracking-[0.4em] mb-6">PART 03</div>
        <div class="text-white/40 text-7xl font-black mb-4">03</div>
        <h1 class="text-[5rem] font-bold text-white leading-tight mb-6">技术架构</h1>
        <div class="w-20 h-1 bg-pink-400 mb-8"></div>
        <p class="text-2xl text-slate-300 max-w-[700px] leading-relaxed">生成器拆成 10 个独立模块，三套 OCR 应对不同 PDF 场景，六项质检加定向修复兜底</p>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(11,`
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
`);window.slideDataMap.set(12,`
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
`);window.slideDataMap.set(13,`
  <div class="w-[1440px] h-[810px] bg-white p-[60px] slide-bg">
    <div class="mb-4"><div class="inline-block bg-emerald-100 text-emerald-700 text-xs px-3 py-1 rounded-full mb-4">质量保障</div></div>
    <h2 class="text-[44px] font-bold text-slate-900 mb-3">六项质检 + 定向修复</h2>
    <p class="text-xl text-slate-500 mb-8">生成完不是终点，质检发现问题就自动重出对应题目，再修一遍 Word 格式</p>
    <div class="grid grid-cols-3 gap-5 mb-8">
      <div class="bg-blue-600 rounded-2xl p-5 text-white">
        <div class="text-white/60 text-xs mb-2">检测项 1</div>
        <p class="text-lg font-bold mb-2">题量一致性</p>
        <p class="text-blue-200 text-sm">实际题量与规划表是否对得上</p>
      </div>
      <div class="bg-blue-600 rounded-2xl p-5 text-white">
        <div class="text-white/60 text-xs mb-2">检测项 2</div>
        <p class="text-lg font-bold mb-2">答案自暴露</p>
        <p class="text-blue-200 text-sm">答案关键词是否出现在题干里</p>
      </div>
      <div class="bg-blue-600 rounded-2xl p-5 text-white">
        <div class="text-white/60 text-xs mb-2">检测项 3</div>
        <p class="text-lg font-bold mb-2">选项失衡</p>
        <p class="text-blue-200 text-sm">选项长度是否明显长短不一</p>
      </div>
      <div class="bg-blue-600 rounded-2xl p-5 text-white">
        <div class="text-white/60 text-xs mb-2">检测项 4</div>
        <p class="text-lg font-bold mb-2">答案分布</p>
        <p class="text-blue-200 text-sm">答案是否过度集中在某个选项</p>
      </div>
      <div class="bg-blue-600 rounded-2xl p-5 text-white">
        <div class="text-white/60 text-xs mb-2">检测项 5</div>
        <p class="text-lg font-bold mb-2">解析质量</p>
        <p class="text-blue-200 text-sm">解析是否过短或没有因果说明</p>
      </div>
      <div class="bg-blue-600 rounded-2xl p-5 text-white">
        <div class="text-white/60 text-xs mb-2">检测项 6</div>
        <p class="text-lg font-bold mb-2">Word 格式</p>
        <p class="text-blue-200 text-sm">公式、答案、解析段落样式是否正常</p>
      </div>
    </div>
    <div class="bg-emerald-50 rounded-2xl p-6 border border-emerald-200">
      <h3 class="text-base font-bold text-emerald-900 mb-4">自动修复能力</h3>
      <div class="grid grid-cols-4 gap-3">
        <div class="bg-emerald-600 rounded-xl p-3 text-center text-white"><p class="font-bold text-sm">答案分布重排</p><p class="text-emerald-200 text-xs mt-1">检测集中后自动重排选项</p></div>
        <div class="bg-emerald-600 rounded-xl p-3 text-center text-white"><p class="font-bold text-sm">公式标记转换</p><p class="text-emerald-200 text-xs mt-1">{math:...} → Word 原生公式</p></div>
        <div class="bg-emerald-600 rounded-xl p-3 text-center text-white"><p class="font-bold text-sm">样式批量修复</p><p class="text-emerald-200 text-xs mt-1">答案/解析格式统一</p></div>
        <div class="bg-emerald-700 rounded-xl p-3 text-center text-white"><p class="font-bold text-sm">定向重出题</p><p class="text-emerald-200 text-xs mt-1">问题题号单独再调一次 API</p></div>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(14,`
  <div class="w-[1440px] h-[810px] bg-gradient-to-br from-emerald-700 to-emerald-900 relative overflow-hidden slide-bg">
    <div class="absolute top-[-150px] right-[-100px] w-[500px] h-[500px] rounded-full bg-white/5 blur-3xl"></div>
    <div class="absolute bottom-[-100px] left-[-100px] w-[400px] h-[400px] rounded-full bg-amber-500/10 blur-3xl"></div>
    <div class="relative z-10 flex items-center h-full px-28">
      <div>
        <div class="text-amber-300 text-sm tracking-[0.4em] mb-6">PART 04</div>
        <div class="text-white/40 text-7xl font-black mb-4">04</div>
        <h1 class="text-[5rem] font-bold text-white leading-tight mb-6">成果与展望</h1>
        <div class="w-20 h-1 bg-amber-400 mb-8"></div>
        <p class="text-2xl text-slate-300 max-w-[700px] leading-relaxed">已经覆盖的省份考类、新增省份的标准化流程，以及后续要继续打磨的方向</p>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(15,`
  <div class="w-[1440px] h-[810px] bg-white p-[60px] slide-bg">
    <div class="mb-4"><div class="inline-block bg-orange-100 text-orange-700 text-xs px-3 py-1 rounded-full mb-4">覆盖范围</div></div>
    <h2 class="text-[44px] font-bold text-slate-900 mb-3">3 省 6 考类已经在跑</h2>
    <p class="text-xl text-slate-500 mb-8">从重庆机械加工类起步，逐步扩展到四川、内蒙古，覆盖了 9 本以上教材</p>
    <div class="grid grid-cols-3 gap-6 mb-7">
      <div class="bg-blue-600 rounded-2xl p-7 text-white">
        <div class="text-5xl font-black mb-2">重庆</div>
        <div class="text-blue-200 text-base font-bold mb-3">5 个考类</div>
        <div class="space-y-1 text-blue-100 text-sm">
          <p>· 机械加工类</p>
          <p>· 汽车类</p>
          <p>· 电气技术类</p>
          <p>· 电子技术类</p>
          <p>· 土建类</p>
        </div>
      </div>
      <div class="bg-cyan-600 rounded-2xl p-7 text-white">
        <div class="text-5xl font-black mb-2">四川</div>
        <div class="text-cyan-200 text-base font-bold mb-3">1 个考类</div>
        <div class="space-y-1 text-cyan-100 text-sm">
          <p>· 汽车类</p>
        </div>
        <div class="mt-5 text-cyan-200/70 text-xs">教材：汽车构造 · 底盘 · 电气</div>
      </div>
      <div class="bg-purple-600 rounded-2xl p-7 text-white">
        <div class="text-5xl font-black mb-2">内蒙</div>
        <div class="text-purple-200 text-base font-bold mb-3">1 个考类</div>
        <div class="space-y-1 text-purple-100 text-sm">
          <p>· 机电类</p>
        </div>
        <div class="mt-5 text-purple-200/70 text-xs">教材：电工 · 电子 · 计算机 · 网络 · 植保</div>
      </div>
    </div>
    <div class="bg-slate-50 rounded-2xl p-6 border border-slate-200 mb-5">
      <h3 class="text-base font-bold text-slate-800 mb-4">新增一个省份的流程</h3>
      <div class="flex items-center gap-2">
        <div class="flex-1 bg-white rounded-lg px-3 py-3 text-center border border-slate-200"><p class="text-slate-700 font-bold text-sm">放考纲 PDF</p></div>
        <span class="text-slate-300">→</span>
        <div class="flex-1 bg-white rounded-lg px-3 py-3 text-center border border-slate-200"><p class="text-slate-700 font-bold text-sm">放教材 PDF</p></div>
        <span class="text-slate-300">→</span>
        <div class="flex-1 bg-white rounded-lg px-3 py-3 text-center border border-slate-200"><p class="text-slate-700 font-bold text-sm">放历年真题</p></div>
        <span class="text-slate-300">→</span>
        <div class="flex-1 bg-purple-50 rounded-lg px-3 py-3 text-center border border-purple-200"><p class="text-purple-700 font-bold text-sm">生成风格库</p></div>
        <span class="text-slate-300">→</span>
        <div class="flex-1 bg-emerald-600 rounded-lg px-3 py-3 text-center"><p class="text-white font-bold text-sm">生成规划表</p></div>
        <span class="text-slate-300">→</span>
        <div class="flex-1 bg-emerald-700 rounded-lg px-3 py-3 text-center"><p class="text-white font-bold text-sm">跑 create.py</p></div>
      </div>
    </div>
    <div class="bg-slate-900 rounded-2xl p-4">
      <div class="flex items-center justify-center gap-6">
        <div class="text-center"><span class="text-white font-bold text-sm">教师版 docx</span></div>
        <span class="text-slate-600">|</span>
        <div class="text-center"><span class="text-white font-bold text-sm">学生版 docx</span></div>
        <span class="text-slate-600">|</span>
        <div class="text-center"><span class="text-white font-bold text-sm">原始 txt</span></div>
        <span class="text-slate-600">|</span>
        <div class="text-center"><span class="text-white font-bold text-sm">zip 批量打包</span></div>
      </div>
    </div>
  </div>
`);window.slideDataMap.set(16,`
  <div class="w-[1440px] h-[810px] bg-slate-900 relative overflow-hidden slide-bg">
    <div class="absolute top-0 right-0 w-[400px] h-[400px] rounded-full bg-blue-600/10 blur-3xl"></div>
    <div class="absolute bottom-0 left-0 w-[300px] h-[300px] rounded-full bg-purple-600/10 blur-3xl"></div>
    <div class="relative z-10 flex items-center h-full px-28">
      <div class="flex-1">
        <h1 class="text-[5.5rem] font-bold text-white mb-6">谢谢</h1>
        <div class="w-20 h-1 bg-blue-500 mb-8"></div>
        <p class="text-3xl text-slate-300 mb-3">一课一练试卷生成工具包</p>
        <p class="text-xl text-slate-400 mb-14">项目介绍 · 2026 年 6 月</p>
        <div class="grid grid-cols-2 gap-x-12 gap-y-3 max-w-[600px]">
          <div class="flex items-center gap-3 text-slate-400"><span class="w-2 h-2 bg-blue-500 rounded-full"></span><span class="text-base">规划表驱动</span></div>
          <div class="flex items-center gap-3 text-slate-400"><span class="w-2 h-2 bg-blue-500 rounded-full"></span><span class="text-base">七层控制体系</span></div>
          <div class="flex items-center gap-3 text-slate-400"><span class="w-2 h-2 bg-blue-500 rounded-full"></span><span class="text-base">真题风格蒸馏</span></div>
          <div class="flex items-center gap-3 text-slate-400"><span class="w-2 h-2 bg-blue-500 rounded-full"></span><span class="text-base">六项质检 + 定向修复</span></div>
          <div class="flex items-center gap-3 text-slate-400"><span class="w-2 h-2 bg-blue-500 rounded-full"></span><span class="text-base">三套 OCR 互补</span></div>
          <div class="flex items-center gap-3 text-slate-400"><span class="w-2 h-2 bg-blue-500 rounded-full"></span><span class="text-base">3 省 6 考类已上线</span></div>
        </div>
      </div>
      <div class="w-[400px] text-right">
        <div class="border-l-2 border-slate-700 pl-8 ml-auto">
          <p class="text-slate-500 text-sm mb-2">问题反馈 / 资料补充</p>
          <p class="text-white text-xl font-bold mb-4">项目维护者</p>
          <p class="text-slate-400 text-sm leading-relaxed">如需新增省份、调整规划表、补充真题风格库，可参照 <span class="text-blue-400">05_项目文档（使用前必读！）</span> 目录下的说明</p>
        </div>
      </div>
    </div>
  </div>
`);

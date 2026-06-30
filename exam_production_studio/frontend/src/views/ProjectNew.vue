<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../services/api'

const route = useRoute()
const router = useRouter()

const TYPES = [
  { value: 'yikeyilian', label: '一课一练', desc: '教材目录基础 · 逐练小卷 · ×1' },
  { value: 'kaogang_100', label: '考纲百套卷', desc: '考纲基础 · 含细目表 · ×1' },
  { value: 'shuangxi', label: '考点双析卷', desc: '考纲基础 · 拉题×2 · 奇偶分卷' },
]

const DEFAULT_VOLUME: Record<string, any[]> = {
  yikeyilian: [
    { type: '单项选择题', count: 5, score_per: 2 },
    { type: '填空题', count: 3, score_per: 2 },
    { type: '综合题', count: 2, score_per: 5 },
  ],
  kaogang_100: [
    { type: '单项选择题', count: 20, score_per: 2 },
    { type: '填空题', count: 10, score_per: 2 },
    { type: '判断题', count: 10, score_per: 1 },
    { type: '简答题', count: 4, score_per: 5 },
    { type: '综合题', count: 2, score_per: 10 },
  ],
  shuangxi: [
    { type: '单项选择题', count: 20, score_per: 2 },
    { type: '填空题', count: 10, score_per: 2 },
    { type: '判断题', count: 10, score_per: 1 },
  ],
}

const form = reactive<any>({
  paper_type: (route.query.type as string) || 'yikeyilian',
  name: '',
  province: '',
  exam_type_name: '高职分类考试',
  exam_category: '',
  course: '',
  textbook: '',
  edition: '',
  paper_range: 'all',
  plan_source: 'ocr',
  output_versions: ['原卷版', '解析版'],
  difficulty: { easy: 80, medium: 10, hard: 10 },
  narrow_point: { enabled: true, merge_threshold: 80 },
  ai: { match: true, summary: true, fill: true, match_threshold: 0.85, max_fix_rounds: 2 },
  volume: JSON.parse(JSON.stringify(DEFAULT_VOLUME['yikeyilian'])),
})

watch(
  () => form.paper_type,
  (t) => {
    form.volume = JSON.parse(JSON.stringify(DEFAULT_VOLUME[t] || DEFAULT_VOLUME['yikeyilian']))
  },
)

function parseRangeCount(s: string): string {
  const t = (s || '').trim()
  if (!t) return '0'
  if (t.toLowerCase() === 'all') return '全部'
  const set = new Set<number>()
  for (let part of t.replace(/，/g, ',').split(',')) {
    part = part.trim()
    if (!part) continue
    if (part.includes('-')) {
      const [a, b] = part.split('-').map((x) => parseInt(x))
      if (isNaN(a) || isNaN(b)) return '格式错误'
      const [lo, hi] = a <= b ? [a, b] : [b, a]
      for (let i = lo; i <= hi; i++) set.add(i)
    } else {
      const n = parseInt(part)
      if (isNaN(n)) return '格式错误'
      set.add(n)
    }
  }
  return String(set.size)
}
const rangeCount = computed(() => parseRangeCount(form.paper_range))
const diffSum = computed(() => form.difficulty.easy + form.difficulty.medium + form.difficulty.hard)

function addRow() {
  form.volume.push({ type: '新题型', count: 1, score_per: 1 })
}
function delRow(i: number) {
  form.volume.splice(i, 1)
}

const saving = ref(false)
async function submit() {
  if (diffSum.value !== 100) return ElMessage.error('难度分布三者之和必须为 100')
  if (!form.output_versions.length) return ElMessage.error('至少选择一个输出版本')
  saving.value = true
  try {
    const by_type: Record<string, any> = {}
    for (const r of form.volume) by_type[r.type] = { count: Number(r.count), score_per: Number(r.score_per) }
    const body = {
      paper_type: form.paper_type,
      name: form.name,
      province: form.province,
      exam_type_name: form.exam_type_name,
      exam_category: form.exam_category,
      course: form.course,
      textbook: form.textbook,
      edition: form.edition,
      paper_range: form.paper_range,
      plan_source: form.plan_source,
      output_versions: form.output_versions,
      volume_config: { by_type, difficulty: form.difficulty, narrow_point: form.narrow_point },
      ai_options: form.ai,
    }
    const p = await api.createProject(body)
    ElMessage.success('项目已创建')
    router.push(`/projects/${p.id}/resources`)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  if (route.query.type) form.paper_type = route.query.type as string
})
</script>

<template>
  <el-card>
    <template #header>项目创建</template>
    <el-form label-width="120px" style="max-width: 920px">
      <el-form-item label="卷类产品">
        <div style="display: flex; gap: 12px; flex-wrap: wrap">
          <el-card
            v-for="t in TYPES"
            :key="t.value"
            shadow="hover"
            :style="{
              width: '220px',
              cursor: 'pointer',
              border: form.paper_type === t.value ? '2px solid #409eff' : '1px solid #eee',
            }"
            @click="form.paper_type = t.value"
          >
            <strong>{{ t.label }}</strong>
            <div style="color: #888; font-size: 12px; margin-top: 6px">{{ t.desc }}</div>
          </el-card>
        </div>
      </el-form-item>

      <el-form-item label="项目名称">
        <el-input v-model="form.name" placeholder="留空将自动按 类型_省份_课程 生成" />
      </el-form-item>
      <el-form-item label="省份（全称）">
        <el-input v-model="form.province" placeholder="如 内蒙古自治区（自治区不简写）" />
      </el-form-item>
      <el-form-item label="考试名称/类型">
        <el-select v-model="form.exam_type_name" allow-create filterable default-first-option style="width: 260px">
          <el-option label="高职分类考试" value="高职分类考试" />
          <el-option label="对口招生" value="对口招生" />
        </el-select>
      </el-form-item>
      <el-form-item label="考类/专业类别">
        <el-input v-model="form.exam_category" placeholder="如 电子与信息大类" />
      </el-form-item>
      <el-form-item label="课程名">
        <el-input v-model="form.course" />
      </el-form-item>
      <el-form-item label="教材名称" v-if="form.paper_type === 'yikeyilian'">
        <el-input v-model="form.textbook" placeholder="如 电工基础" />
      </el-form-item>
      <el-form-item label="出版社·版次" v-if="form.paper_type === 'yikeyilian'">
        <el-input v-model="form.edition" placeholder="如 高教版·第三版" />
      </el-form-item>

      <el-form-item label="卷号范围">
        <el-input v-model="form.paper_range" style="width: 260px" placeholder="all / 1-5 / 3,7,12" />
        <el-tag style="margin-left: 12px" type="success">将生成 {{ rangeCount }} 套</el-tag>
      </el-form-item>
      <el-form-item label="规划表来源">
        <el-radio-group v-model="form.plan_source">
          <el-radio value="ocr">本地OCR扫描/合成</el-radio>
          <el-radio value="upload">上传 xlsx</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="拉题倍率">
        <el-tag>{{ form.paper_type === 'shuangxi' ? '2（双析自动）' : '1' }}</el-tag>
      </el-form-item>

      <el-form-item label="题型/题量/分值">
        <el-table :data="form.volume" size="small" style="width: 560px">
          <el-table-column label="题型">
            <template #default="{ row }"><el-input v-model="row.type" size="small" /></template>
          </el-table-column>
          <el-table-column label="题量" width="110">
            <template #default="{ row }"><el-input-number v-model="row.count" :min="0" size="small" /></template>
          </el-table-column>
          <el-table-column label="分值" width="110">
            <template #default="{ row }"><el-input-number v-model="row.score_per" :min="0" size="small" /></template>
          </el-table-column>
          <el-table-column width="70">
            <template #default="{ $index }">
              <el-button size="small" type="danger" link @click="delRow($index)">删</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-button size="small" style="margin-top: 8px" @click="addRow">+ 增加题型</el-button>
      </el-form-item>

      <el-form-item label="难度分布">
        <span style="margin-right: 8px">简单</span>
        <el-input-number v-model="form.difficulty.easy" :min="0" :max="100" size="small" />
        <span style="margin: 0 8px">适中</span>
        <el-input-number v-model="form.difficulty.medium" :min="0" :max="100" size="small" />
        <span style="margin: 0 8px">困难</span>
        <el-input-number v-model="form.difficulty.hard" :min="0" :max="100" size="small" />
        <el-tag :type="diffSum === 100 ? 'success' : 'danger'" style="margin-left: 12px">合计 {{ diffSum }}</el-tag>
      </el-form-item>

      <el-form-item label="窄考点合并">
        <el-switch v-model="form.narrow_point.enabled" />
        <span style="margin: 0 8px">阈值</span>
        <el-input-number v-model="form.narrow_point.merge_threshold" :min="0" size="small" />
      </el-form-item>

      <el-form-item label="输出版本">
        <el-checkbox-group v-model="form.output_versions">
          <el-checkbox value="原卷版">原卷版</el-checkbox>
          <el-checkbox value="解析版">解析版</el-checkbox>
        </el-checkbox-group>
      </el-form-item>

      <el-form-item label="AI 辅助">
        <el-switch v-model="form.ai.match" active-text="匹配" />
        <el-switch v-model="form.ai.summary" active-text="摘要" style="margin-left: 12px" />
        <el-switch v-model="form.ai.fill" active-text="补题" style="margin-left: 12px" />
      </el-form-item>
      <el-form-item label="信度阈值 / 修复轮数">
        <el-input-number v-model="form.ai.match_threshold" :min="0" :max="1" :step="0.05" size="small" />
        <el-input-number v-model="form.ai.max_fix_rounds" :min="0" size="small" style="margin-left: 12px" />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" :loading="saving" @click="submit">保存并进入资源导入</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

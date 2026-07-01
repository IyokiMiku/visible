<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../services/api'

const route = useRoute()
const id = route.params.id as string

interface Entry {
  name: string
  path: string
  is_dir: boolean
  size: number
  mtime: number
  suffix: string
}
interface TreeNode {
  label: string
  name: string
  path: string
  is_dir: boolean
  suffix: string
  children?: TreeNode[]
}

const loading = ref(false)
const treeData = ref<TreeNode[]>([])
const defaultExpanded = ref<string[]>([])

const IMAGE_EXT = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']
const TEXT_EXT = ['.md', '.txt', '.log', '.csv', '.tpl']

// 由扁平列表拼出目录树（后端按 path 升序返回，父目录先于子项）
function buildTree(entries: Entry[]): TreeNode[] {
  const roots: TreeNode[] = []
  const map = new Map<string, TreeNode>()
  for (const e of entries) {
    const node: TreeNode = { label: e.name, name: e.name, path: e.path, is_dir: e.is_dir, suffix: e.suffix }
    if (e.is_dir) node.children = []
    map.set(e.path, node)
    // 父路径：去掉最后一段（path 用系统分隔符，统一按 / 和 \ 处理）
    const parts = e.path.split(/[\\/]/)
    parts.pop()
    const parentPath = parts.join('\\')
    const parent = map.get(parentPath) || map.get(parts.join('/'))
    if (parent && parent.children) parent.children.push(node)
    else roots.push(node)
  }
  return roots
}

async function loadTree() {
  loading.value = true
  try {
    const res: any = await api.artifactTree(id)
    treeData.value = buildTree(res.entries || [])
    defaultExpanded.value = treeData.value.map((n) => n.path)
  } finally {
    loading.value = false
  }
}

// ===== 预览区 =====
const selected = ref<TreeNode | null>(null)
const previewLoading = ref(false)
const kind = ref<'empty' | 'json' | 'state' | 'text' | 'xlsx' | 'image' | 'pdf' | 'binary'>('empty')
const textContent = ref('')
const jsonContent = ref('')
const stateData = ref<any>(null)
const xlsxSheets = ref<Array<{ name: string; rows: any[][] }>>([])

function iconOf(node: TreeNode): string {
  if (node.is_dir) return '📁'
  if (IMAGE_EXT.includes(node.suffix)) return '🖼'
  if (node.suffix === '.json') return '{ }'
  if (node.suffix === '.xlsx') return '▦'
  if (node.suffix === '.docx') return '📄'
  if (node.suffix === '.pdf') return '📕'
  if (node.suffix === '.zip') return '🗜'
  return '📃'
}

async function fetchText(path: string): Promise<string> {
  const resp = await fetch(api.downloadUrl(id, path))
  if (!resp.ok) throw new Error('读取失败')
  return await resp.text()
}

async function onNodeClick(node: TreeNode) {
  if (node.is_dir) return
  selected.value = node
  previewLoading.value = true
  try {
    if (IMAGE_EXT.includes(node.suffix)) {
      kind.value = 'image'
    } else if (node.suffix === '.pdf') {
      kind.value = 'pdf'
    } else if (node.suffix === '.xlsx') {
      const res: any = await api.previewXlsx(id, node.path)
      xlsxSheets.value = res.sheets || []
      kind.value = 'xlsx'
    } else if (node.suffix === '.json') {
      const raw = await fetchText(node.path)
      let parsed: any = null
      try {
        parsed = JSON.parse(raw)
      } catch {
        /* 非法 JSON 就当文本看 */
      }
      if (node.name === 'state.json' && parsed) {
        stateData.value = parsed
        kind.value = 'state'
      } else {
        jsonContent.value = parsed ? JSON.stringify(parsed, null, 2) : raw
        kind.value = 'json'
      }
    } else if (TEXT_EXT.includes(node.suffix) || node.suffix === '') {
      textContent.value = await fetchText(node.path)
      kind.value = 'text'
    } else {
      kind.value = 'binary'
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '预览失败')
    kind.value = 'binary'
  } finally {
    previewLoading.value = false
  }
}

function download(path: string) {
  window.open(api.downloadUrl(id, path), '_blank')
}
const currentImageUrl = computed(() =>
  selected.value ? api.downloadUrl(id, selected.value.path) : '',
)

onMounted(loadTree)
</script>

<template>
  <el-card>
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <span>中间文件浏览（04_生成输出）</span>
        <el-button size="small" :loading="loading" @click="loadTree">刷新</el-button>
      </div>
    </template>

    <el-row :gutter="16">
      <el-col :span="8">
        <div v-loading="loading" class="tree-pane">
          <el-tree
            :data="treeData"
            node-key="path"
            :props="{ label: 'label', children: 'children' }"
            :default-expanded-keys="defaultExpanded"
            :expand-on-click-node="false"
            highlight-current
            @node-click="onNodeClick"
          >
            <template #default="{ data }">
              <span class="node">
                <span class="node-icon">{{ iconOf(data) }}</span>
                <span :class="{ 'node-dir': data.is_dir }">{{ data.label }}</span>
              </span>
            </template>
          </el-tree>
          <el-empty v-if="!loading && !treeData.length" description="暂无中间文件（项目还没跑过流程）" />
        </div>
      </el-col>

      <el-col :span="16">
        <div v-loading="previewLoading" class="preview-pane">
          <div v-if="kind === 'empty'" class="hint">← 从左侧选择文件查看内容</div>

          <template v-else>
            <div class="preview-head">
              <span class="preview-name">{{ selected?.name }}</span>
              <el-button size="small" @click="download(selected!.path)">下载</el-button>
            </div>

            <!-- state.json 看板 -->
            <div v-if="kind === 'state'">
              <el-divider content-position="left">已完成的前置阶段</el-divider>
              <div class="tags">
                <el-tag v-for="s in stateData?.stages || []" :key="s" type="success">{{ s }}</el-tag>
                <span v-if="!(stateData?.stages || []).length" class="muted">（无）</span>
              </div>
              <el-divider content-position="left">已完成的卷</el-divider>
              <div class="tags">
                <el-tag v-for="p in stateData?.papers_done || []" :key="p">第 {{ p }} 卷</el-tag>
                <span v-if="!(stateData?.papers_done || []).length" class="muted">（无）</span>
              </div>
              <el-divider content-position="left">原始 JSON</el-divider>
              <pre class="code">{{ JSON.stringify(stateData, null, 2) }}</pre>
            </div>

            <!-- JSON -->
            <pre v-else-if="kind === 'json'" class="code">{{ jsonContent }}</pre>

            <!-- 纯文本 / markdown -->
            <pre v-else-if="kind === 'text'" class="code text">{{ textContent }}</pre>

            <!-- xlsx 表格 -->
            <div v-else-if="kind === 'xlsx'">
              <template v-for="sheet in xlsxSheets" :key="sheet.name">
                <el-divider content-position="left">{{ sheet.name }}</el-divider>
                <div class="table-wrap">
                  <table class="xlsx">
                    <tbody>
                      <tr v-for="(row, ri) in sheet.rows" :key="ri">
                        <td v-for="(cell, ci) in row" :key="ci">{{ cell }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </template>
            </div>

            <!-- 图片 -->
            <div v-else-if="kind === 'image'" class="image-wrap">
              <img :src="currentImageUrl" alt="预览" />
            </div>

            <!-- PDF -->
            <iframe v-else-if="kind === 'pdf'" :src="currentImageUrl" class="pdf" />

            <!-- 其它二进制（docx/zip 等） -->
            <el-empty v-else description="该类型无法内联预览，请下载后查看" />
          </template>
        </div>
      </el-col>
    </el-row>
  </el-card>
</template>

<style scoped>
.tree-pane {
  min-height: 640px;
  max-height: 75vh;
  overflow: auto;
  border: 1px solid #eee;
  border-radius: 6px;
  padding: 8px;
}
.preview-pane {
  min-height: 640px;
  max-height: 75vh;
  overflow: auto;
  border: 1px solid #eee;
  border-radius: 6px;
  padding: 12px;
}
.node {
  display: flex;
  align-items: center;
  gap: 6px;
}
.node-icon {
  width: 18px;
  text-align: center;
  font-size: 12px;
}
.node-dir {
  font-weight: 600;
}
.hint,
.muted {
  color: var(--el-text-color-secondary);
}
.hint {
  padding: 24px;
}
.preview-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.preview-name {
  font-weight: 600;
  word-break: break-all;
}
.code {
  background: #f7f8fa;
  border: 1px solid #eee;
  border-radius: 6px;
  padding: 12px;
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
.text {
  white-space: pre-wrap;
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.table-wrap {
  overflow-x: auto;
}
table.xlsx {
  border-collapse: collapse;
  font-size: 12px;
}
table.xlsx td {
  border: 1px solid #dcdfe6;
  padding: 3px 8px;
  white-space: nowrap;
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.image-wrap img {
  max-width: 100%;
}
.pdf {
  width: 100%;
  height: 70vh;
  border: 1px solid #eee;
}
</style>

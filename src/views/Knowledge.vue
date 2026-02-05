<template>
  <div class="knowledge-page">
    <!-- LightRAG 配置：仅 Gemini API -->
    <el-card class="rag-config-card">
      <template #header>
        <span>LightRAG 配置</span>
        <span class="config-hint">（使用 Gemini API，见 Google AI Studio 获取 Key）</span>
      </template>
      <el-form :model="ragConfig" label-width="120" style="max-width: 480px">
        <el-form-item label="Gemini API Key">
          <el-input v-model="ragConfig.api_key" type="password" placeholder="Gemini API Key" show-password clearable />
        </el-form-item>
        <el-form-item label="LLM 模型">
          <el-input v-model="ragConfig.llm_model" placeholder="如 gemini-2.0-flash" />
        </el-form-item>
        <el-form-item label="Embedding 模型">
          <el-input v-model="ragConfig.embed_model" placeholder="如 gemini-embedding-001" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveRagConfig">保存配置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card>
      <template #header>
        <span>知识库 RAG（LightRAG + Neo4j）</span>
        <el-button type="primary" style="float: right" @click="showKbDialog()">新建知识库</el-button>
      </template>
      <el-table :data="kbList" stripe>
        <el-table-column prop="name" label="名称" min-width="120" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column label="知识图谱状态" width="200">
          <template #default="{ row }">
            <div v-if="row.kg_status === 'building'" class="status-building">
              <el-progress
                :percentage="row.kg_progress"
                :stroke-width="8"
                :status="row.kg_status === 'failed' ? 'exception' : undefined"
              />
              <span class="status-text">构建中</span>
            </div>
            <el-tag v-else-if="row.kg_status === 'success'" type="success">构建成功</el-tag>
            <el-tag v-else-if="row.kg_status === 'failed'" type="danger">
              构建失败
              <el-button link type="danger" size="small" @click="openBuildErrorDialog(row.kg_error)">查看错误详情</el-button>
            </el-tag>
            <el-tag v-else type="info">待构建</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="showDocPanel(row)">文档</el-button>
            <el-button link type="primary" @click="openGraphDialog(row)">查看知识图谱</el-button>
            <el-button link type="primary" @click="showKbDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="onDeleteKb(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建/编辑知识库 -->
    <el-dialog v-model="kbDialogVisible" :title="editingKbId ? '编辑知识库' : '新建知识库'" width="480">
      <el-form ref="kbFormRef" :model="kbForm" :rules="kbRules" label-width="80">
        <el-form-item label="名称" prop="name">
          <el-input v-model="kbForm.name" placeholder="知识库名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="kbForm.description" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="kbDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="kbSaving" @click="submitKb">确定</el-button>
      </template>
    </el-dialog>

    <!-- 文档管理抽屉 -->
    <el-drawer
      v-model="docDrawerVisible"
      :title="`文档管理：${currentKb?.name || ''}`"
      size="520"
      direction="rtl"
    >
      <div v-if="currentKb" class="doc-drawer">
        <div class="status-line">
          <span>知识图谱状态：</span>
          <template v-if="currentKb.kg_status === 'building'">
            <el-progress :percentage="currentKb.kg_progress" :stroke-width="6" style="width: 120px; display: inline-block; margin: 0 8px" />
            <span>构建中</span>
          </template>
          <el-tag v-else-if="currentKb.kg_status === 'success'" type="success" size="small">构建成功</el-tag>
          <el-tag v-else-if="currentKb.kg_status === 'failed'" type="danger" size="small">
            构建失败
            <el-button link type="danger" size="small" @click="openBuildErrorDialog(currentKb.kg_error)">查看错误详情</el-button>
          </el-tag>
          <el-tag v-else type="info" size="small">待构建</el-tag>
        </div>
        <div class="build-row">
          <el-upload
            class="upload-area"
            :auto-upload="true"
            :show-file-list="false"
            :http-request="(opt) => uploadFile(opt.file)"
            accept=".txt,.pdf,.docx,.doc"
          >
            <el-button type="primary">上传文件（TXT/PDF/Word）</el-button>
          </el-upload>
          <el-button
            type="success"
            :loading="building"
            :disabled="currentKb.kg_status === 'building' || !hasPendingDocs"
            @click="triggerBuild"
          >
            构建知识图谱
          </el-button>
        </div>
        <el-table :data="docList" stripe size="small">
          <el-table-column prop="filename" label="文件名" />
          <el-table-column prop="file_type" label="类型" width="70" />
          <el-table-column label="参与构建" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.build_status === 'built'" type="success" size="small">已参与</el-tag>
              <el-tag v-else-if="row.build_status === 'building'" type="warning" size="small">构建中</el-tag>
              <el-tag v-else-if="row.build_status === 'failed'" type="danger" size="small">失败</el-tag>
              <el-tag v-else type="info" size="small">未参与</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button link type="danger" @click="deleteDoc(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-drawer>

    <!-- 构建错误详情弹窗（持久展示，便于分析） -->
    <el-dialog
      v-model="buildErrorDialogVisible"
      title="构建失败 - 错误详情"
      width="640px"
      class="build-error-dialog"
      destroy-on-close
      @closed="buildErrorDetail = ''"
    >
      <div class="build-error-content">
        <p class="build-error-hint">请根据下方报错信息检查：LightRAG 配置（API Key/Base URL）、Neo4j 是否启动、依赖是否安装（pip install lightrag-hku neo4j）。</p>
        <el-input
          v-model="buildErrorDetail"
          type="textarea"
          :rows="16"
          readonly
          class="build-error-text"
        />
        <div class="build-error-actions">
          <el-button @click="copyBuildError">复制到剪贴板</el-button>
          <el-button type="primary" @click="buildErrorDialogVisible = false">关闭</el-button>
        </div>
      </div>
    </el-dialog>

    <!-- 知识图谱弹窗 -->
    <el-dialog
      v-model="graphDialogVisible"
      title="知识图谱"
      width="90%"
      top="3vh"
      destroy-on-close
      class="graph-dialog"
      @opened="initGraphChart"
      @closed="disposeGraphChart"
    >
      <div v-if="graphLoading" class="graph-loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载中...</span>
      </div>
      <div v-else-if="graphError" class="graph-error">{{ graphError }}</div>
      <div ref="graphChartRef" class="graph-chart"></div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { WarningFilled, Loading } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { knowledge as knowledgeApi } from '../api'

const kbList = ref([])
const kbDialogVisible = ref(false)
const editingKbId = ref(null)
const kbSaving = ref(false)
const kbFormRef = ref()
const kbForm = reactive({ name: '', description: '' })
const kbRules = { name: [{ required: true, message: '请输入名称' }] }

const docDrawerVisible = ref(false)
const currentKb = ref(null)
const docList = ref([])
const pollTimer = ref(null)
const building = ref(false)
const ragConfig = reactive({
  api_key: '',
  llm_model: 'gemini-2.0-flash',
  embed_model: 'gemini-embedding-001',
})

const graphDialogVisible = ref(false)
const graphChartRef = ref(null)
const graphLoading = ref(false)
const graphError = ref('')
let chartInstance = null

const buildErrorDialogVisible = ref(false)
const buildErrorDetail = ref('')

function openBuildErrorDialog(errorText) {
  buildErrorDetail.value = errorText || '无错误信息'
  buildErrorDialogVisible.value = true
}

function copyBuildError() {
  try {
    navigator.clipboard.writeText(buildErrorDetail.value)
    ElMessage.success('已复制到剪贴板')
  } catch (_) {
    ElMessage.error('复制失败')
  }
}

const loadKbs = async () => {
  try {
    kbList.value = await knowledgeApi.list()
    pollingBuilding()
  } catch (e) {
    ElMessage.error(e.detail || e.message || '加载失败')
  }
}

const pollingBuilding = () => {
  if (pollTimer.value) clearInterval(pollTimer.value)
  const building = kbList.value.filter((k) => k.kg_status === 'building')
  if (building.length === 0) return
  pollTimer.value = setInterval(async () => {
    for (const k of building) {
      try {
        const st = await knowledgeApi.getStatus(k.id)
        const row = kbList.value.find((r) => r.id === k.id)
        const wasBuilding = row && row.kg_status === 'building'
        if (row) {
          row.kg_status = st.status
          row.kg_progress = st.progress ?? row.kg_progress
          row.kg_error = st.error ?? row.kg_error
          if (wasBuilding && st.status === 'failed' && st.error) {
            openBuildErrorDialog(st.error)
          }
        }
        if (currentKb.value?.id === k.id) {
          currentKb.value.kg_status = st.status
          currentKb.value.kg_progress = st.progress ?? currentKb.value.kg_progress
          currentKb.value.kg_error = st.error ?? currentKb.value.kg_error
        }
      } catch (_) {}
    }
    const stillBuilding = kbList.value.filter((k) => k.kg_status === 'building')
    if (stillBuilding.length === 0 && pollTimer.value) {
      clearInterval(pollTimer.value)
      pollTimer.value = null
    }
  }, 1500)
}

const showKbDialog = (row) => {
  editingKbId.value = row?.id ?? null
  kbForm.name = row?.name ?? ''
  kbForm.description = row?.description ?? ''
  kbDialogVisible.value = true
}

const submitKb = async () => {
  await kbFormRef.value?.validate()
  kbSaving.value = true
  try {
    if (editingKbId.value) {
      await knowledgeApi.update(editingKbId.value, { name: kbForm.name, description: kbForm.description })
      ElMessage.success('已更新')
    } else {
      await knowledgeApi.create({ name: kbForm.name, description: kbForm.description })
      ElMessage.success('已创建')
    }
    kbDialogVisible.value = false
    loadKbs()
  } catch (e) {
    ElMessage.error(e.detail || e.message || '操作失败')
  } finally {
    kbSaving.value = false
  }
}

const onDeleteKb = async (row) => {
  await ElMessageBox.confirm('确定删除该知识库？文档与图谱数据将一并删除。', '提示', { type: 'warning' })
  await knowledgeApi.delete(row.id)
  ElMessage.success('已删除')
  loadKbs()
}

const hasPendingDocs = computed(() => docList.value.some((d) => d.build_status === 'pending'))

const showDocPanel = async (row) => {
  currentKb.value = { ...row }
  docDrawerVisible.value = true
  try {
    docList.value = await knowledgeApi.listDocuments(row.id)
  } catch (e) {
    ElMessage.error(e.detail || e.message || '加载文档失败')
  }
}

const loadRagConfig = async () => {
  try {
    const c = await knowledgeApi.getRagConfig()
    ragConfig.api_key = c.api_key || ''
    ragConfig.llm_model = c.llm_model || 'gemini-2.0-flash'
    ragConfig.embed_model = c.embed_model || 'gemini-embedding-001'
  } catch (_) {}
}

const saveRagConfig = async () => {
  try {
    await knowledgeApi.updateRagConfig({
      api_key: ragConfig.api_key,
      llm_model: ragConfig.llm_model,
      embed_model: ragConfig.embed_model,
    })
    ElMessage.success('已保存')
    loadRagConfig()
  } catch (e) {
    ElMessage.error(e.detail || e.message || '保存失败')
  }
}

const triggerBuild = async () => {
  if (!currentKb.value || building.value) return
  building.value = true
  try {
    const res = await knowledgeApi.build(currentKb.value.id)
    ElMessage.success(res.message || '已开始构建')
    currentKb.value.kg_status = 'building'
    currentKb.value.kg_progress = 0
    const row = kbList.value.find((r) => r.id === currentKb.value.id)
    if (row) {
      row.kg_status = 'building'
      row.kg_progress = 0
    }
    pollingBuilding()
    docList.value = await knowledgeApi.listDocuments(currentKb.value.id)
  } catch (e) {
    const msg = e.detail || e.message || '构建失败'
    ElMessage.error(msg)
    openBuildErrorDialog(typeof msg === 'string' ? msg : JSON.stringify(e, null, 2))
  } finally {
    building.value = false
  }
}

watch(docDrawerVisible, (v) => {
  if (v && currentKb.value) pollingBuilding()
})

const uploadFile = async (file) => {
  if (!currentKb.value) return
  try {
    await knowledgeApi.upload(currentKb.value.id, file)
    ElMessage.success('上传成功，请点击「构建知识图谱」参与构建')
    docList.value = await knowledgeApi.listDocuments(currentKb.value.id)
  } catch (e) {
    ElMessage.error(e.detail || e.message || '上传失败')
  }
}

const deleteDoc = async (doc) => {
  await ElMessageBox.confirm('确定删除该文档？', '提示', { type: 'warning' })
  await knowledgeApi.deleteDocument(currentKb.value.id, doc.id)
  docList.value = await knowledgeApi.listDocuments(currentKb.value.id)
  ElMessage.success('已删除')
}

const openGraphDialog = (row) => {
  currentKb.value = { ...row }
  graphDialogVisible.value = true
}

const initGraphChart = async () => {
  if (!graphChartRef.value || !currentKb.value) return
  graphLoading.value = true
  graphError.value = ''
  try {
    const data = await knowledgeApi.getGraph(currentKb.value.id)
    const nodes = data.nodes || []
    const edges = data.edges || []
    if (nodes.length === 0) {
      graphError.value = '暂无图谱数据，请先上传文档并等待构建完成。'
      graphLoading.value = false
      return
    }
    await nextTick()
    if (!chartInstance) {
      chartInstance = echarts.init(graphChartRef.value)
    }
    const categories = [...new Set(nodes.map((n) => n.label || 'Node'))]
    const categoryIndex = (label) => {
      const i = categories.indexOf(label || 'Node')
      return i >= 0 ? i : 0
    }
    const option = {
      tooltip: {},
      legend: { data: [] },
      series: [
        {
          type: 'graph',
          layout: 'force',
          data: nodes.map((n) => ({
            id: n.id,
            name: n.name || n.id,
            symbolSize: 28,
            category: categoryIndex(n.label),
          })),
          links: edges.map((e) => ({
            source: e.source,
            target: e.target,
            value: e.type,
          })),
          categories: categories.map((c) => ({ name: c })),
          roam: true,
          label: { show: true, position: 'right', formatter: '{b}' },
          force: {
            repulsion: 200,
            edgeLength: 80,
          },
          lineStyle: { curveness: 0.2 },
        },
      ],
    }
    chartInstance.setOption(option)
  } catch (e) {
    graphError.value = e.detail || e.message || '加载图谱失败'
  } finally {
    graphLoading.value = false
  }
}

const disposeGraphChart = () => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
}

onMounted(() => {
  loadKbs()
  loadRagConfig()
})
</script>

<style scoped>
.knowledge-page { padding: 0; }
.status-building { display: flex; align-items: center; gap: 8px; }
.status-building .el-progress { flex: 0 0 80px; }
.status-text { font-size: 12px; color: #64748b; }
.info-icon { margin-left: 4px; cursor: help; }
.doc-drawer .status-line { margin-bottom: 16px; }
.doc-drawer .upload-area { margin-bottom: 16px; }
.graph-dialog :deep(.el-dialog__body) { height: 75vh; min-height: 400px; }
.graph-loading, .graph-error {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #64748b;
}
.graph-error { color: #dc2626; }
.graph-chart { width: 100%; height: 100%; min-height: 360px; }
.rag-config-card { margin-bottom: 20px; }
.config-hint { font-size: 12px; color: #64748b; margin-left: 8px; }
.build-row { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.build-error-dialog .build-error-hint { color: #64748b; font-size: 13px; margin-bottom: 12px; }
.build-error-dialog .build-error-text { font-family: ui-monospace, monospace; font-size: 12px; }
.build-error-dialog .build-error-actions { margin-top: 12px; }
</style>

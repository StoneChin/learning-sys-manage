<template>
  <div class="models-page">
    <el-card>
      <template #header>
        <span>模型配置</span>
        <el-button type="primary" style="float: right" @click="showDialog()">添加配置</el-button>
      </template>
      <el-table :data="list" stripe>
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="model_type" label="类型">
          <template #default="{ row }">{{ row.model_type === 'api' ? 'API' : '本地' }}</template>
        </el-table-column>
        <el-table-column prop="provider" label="提供商" />
        <el-table-column prop="model_name" label="模型名称" />
        <el-table-column prop="is_default" label="默认">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="success">是</el-tag>
            <el-button v-else link type="primary" @click="setDefault(row)">设为默认</el-button>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button link type="primary" @click="showDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="download-section">
      <template #header>ModelScope 下载基座模型</template>
      <el-form :inline="true">
        <el-form-item label="模型">
          <el-select v-model="downloadModelId" placeholder="选择模型" style="width: 280px">
            <el-option v-for="m in modelscopeList" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="保存目录">
          <el-input v-model="downloadDir" placeholder="例如: ./models" style="width: 200px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="downloading" @click="onDownload">下载</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editId ? '编辑配置' : '添加配置'" width="520">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100">
        <el-form-item label="配置名称" prop="name">
          <el-input v-model="form.name" placeholder="例如: DeepSeek API" />
        </el-form-item>
        <el-form-item label="模型类型" prop="model_type">
          <el-radio-group v-model="form.model_type">
            <el-radio value="api">API</el-radio>
            <el-radio value="local">本地</el-radio>
          </el-radio-group>
        </el-form-item>
        <template v-if="form.model_type === 'api'">
          <el-form-item label="提供商" prop="provider">
            <el-select v-model="form.provider" placeholder="选择" style="width: 100%">
              <el-option label="硅基流动（默认）" value="siliconflow" />
              <el-option label="Gemini" value="gemini" />
            </el-select>
          </el-form-item>
          <el-form-item label="模型名称" prop="model_name">
            <el-input
              v-model="form.model_name"
              :placeholder="
                form.provider === 'gemini'
                  ? '例如: gemini-2.0-flash, gemini-2.5-flash'
                  : '例如: Qwen/Qwen3-8B'
              "
            />
          </el-form-item>
          <el-form-item label="API Base">
            <el-input v-model="form.api_base" :placeholder="form.provider === 'siliconflow' ? '留空使用 https://api.siliconflow.cn/v1' : '留空使用默认'" />
          </el-form-item>
          <el-form-item label="API Key" prop="api_key">
            <el-input
              v-model="form.api_key"
              type="password"
              :placeholder="
                form.provider === 'gemini' ? '可选，留空使用 .env 中 GEMINI_API_KEY' : '硅基流动 API Key'
              "
              show-password
            />
          </el-form-item>
        </template>
        <template v-else>
          <el-form-item label="提供商">
            <span>Ollama 本机</span>
          </el-form-item>
          <el-form-item label="本地模型">
            <el-select v-model="form.model_name" placeholder="选择本地模型" filterable style="width: 100%">
              <el-option v-for="m in localList" :key="m" :label="m" :value="m" />
            </el-select>
          </el-form-item>
          <el-form-item label="本地路径">
            <el-input v-model="form.local_path" placeholder="模型完整路径（可选）" />
          </el-form-item>
          <el-form-item label="API Base">
            <el-input v-model="form.api_base" placeholder="Ollama 地址，如 http://127.0.0.1:11434/v1" />
          </el-form-item>
        </template>
        <el-form-item label="设为默认">
          <el-switch v-model="form.is_default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="loading" @click="onSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { models as modelsApi } from '../api'

const list = ref([])
const localList = ref([])
const modelscopeList = ref([])
const dialogVisible = ref(false)
const editId = ref(null)
const loading = ref(false)
const downloading = ref(false)
const downloadModelId = ref('')
const downloadDir = ref('./models')
const formRef = ref()
const form = reactive({
  name: '',
  model_type: 'api',
  provider: 'siliconflow',
  model_name: '',
  api_base: '',
  api_key: '',
  local_path: '',
  is_default: false,
})
const rules = {
  name: [{ required: true, message: '请输入配置名称' }],
  model_name: [{ required: true, message: '请输入或选择模型名称' }],
}

const load = async () => {
  list.value = await modelsApi.list()
  localList.value = (await modelsApi.localList()).models || []
  modelscopeList.value = (await modelsApi.modelscopeList()).models || []
}

const showDialog = (row) => {
  editId.value = row?.id || null
  form.name = row?.name || ''
  form.model_type = row?.model_type || 'api'
  form.provider = row?.provider || 'siliconflow'
  form.model_name = row?.model_name || ''
  form.api_base = row?.api_base || ''
  form.api_key = row?.api_key === '***' ? '' : (row?.api_key || '')
  form.local_path = row?.local_path || ''
  form.is_default = row?.is_default || false
  dialogVisible.value = true
}

const onSubmit = async () => {
  await formRef.value?.validate()
  loading.value = true
  try {
    const payload = {
      name: form.name,
      model_type: form.model_type,
      provider: form.provider,
      model_name: form.model_name,
      api_base: form.api_base || undefined,
      api_key: form.api_key || undefined,
      local_path: form.local_path || undefined,
      is_default: form.is_default,
    }
    if (editId.value) {
      await modelsApi.update(editId.value, payload)
      ElMessage.success('已更新')
    } else {
      await modelsApi.create(payload)
      ElMessage.success('已添加')
    }
    dialogVisible.value = false
    load()
  } catch (e) {
    ElMessage.error(e.detail || e.message || '操作失败')
  } finally {
    loading.value = false
  }
}

const setDefault = async (row) => {
  await modelsApi.update(row.id, { is_default: true })
  ElMessage.success('已设为默认')
  load()
}

const onDelete = async (row) => {
  await ElMessageBox.confirm('确定删除该配置？', '提示', { type: 'warning' })
  await modelsApi.delete(row.id)
  ElMessage.success('已删除')
  load()
}

const onDownload = async () => {
  if (!downloadModelId.value || !downloadDir.value) {
    ElMessage.warning('请选择模型和保存目录')
    return
  }
  downloading.value = true
  try {
    const res = await modelsApi.modelscopeDownload(downloadModelId.value, downloadDir.value)
    if (res.success) ElMessage.success('下载完成: ' + res.path)
    else ElMessage.error(res.error || '下载失败')
  } catch (e) {
    ElMessage.error(e.detail || e.message || '下载失败')
  } finally {
    downloading.value = false
  }
}

onMounted(load)
watch(dialogVisible, (v) => v && load())
watch(
  () => form.model_type,
  (t) => {
    if (t === 'local') form.provider = 'ollama'
    else if (t === 'api' && form.provider === 'ollama') form.provider = 'siliconflow'
  }
)
</script>

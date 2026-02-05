<template>
  <div class="prompts-page">
    <el-card>
      <template #header>
        <span>Prompt 配置</span>
        <el-button type="primary" style="float: right" @click="showDialog()">添加 Prompt</el-button>
      </template>
      <el-table :data="list" stripe>
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="content" label="内容" show-overflow-tooltip />
        <el-table-column prop="is_default" label="默认" width="80">
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

    <el-dialog v-model="dialogVisible" :title="editId ? '编辑 Prompt' : '添加 Prompt'" width="560">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="例如: 默认助手" />
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="8" placeholder="系统 Prompt，将作为大模型的初始化指令" />
        </el-form-item>
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
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { prompts as promptsApi } from '../api'

const list = ref([])
const dialogVisible = ref(false)
const editId = ref(null)
const loading = ref(false)
const formRef = ref()
const form = reactive({ name: '', content: '', is_default: false })
const rules = {
  name: [{ required: true, message: '请输入名称' }],
  content: [{ required: true, message: '请输入内容' }],
}

const load = async () => {
  list.value = await promptsApi.list()
}

const showDialog = (row) => {
  editId.value = row?.id || null
  form.name = row?.name || ''
  form.content = row?.content || ''
  form.is_default = row?.is_default || false
  dialogVisible.value = true
}

const onSubmit = async () => {
  await formRef.value?.validate()
  loading.value = true
  try {
    if (editId.value) {
      await promptsApi.update(editId.value, form)
      ElMessage.success('已更新')
    } else {
      await promptsApi.create(form)
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
  await promptsApi.update(row.id, { is_default: true })
  ElMessage.success('已设为默认')
  load()
}

const onDelete = async (row) => {
  await ElMessageBox.confirm('确定删除该 Prompt？', '提示', { type: 'warning' })
  await promptsApi.delete(row.id)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

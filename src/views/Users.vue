<template>
  <div class="users-page">
    <el-card>
      <template #header>
        <span>助教管理</span>
        <el-button type="primary" style="float: right" @click="showDialog()">添加助教</el-button>
      </template>
      <el-table :data="list" stripe>
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column prop="full_name" label="姓名" />
        <el-table-column prop="is_active" label="状态">
          <template #default="{ row }">{{ row.is_active ? '正常' : '禁用' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="primary" @click="showDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editId ? '编辑助教' : '添加助教'" width="400">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="!!editId" placeholder="用户名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" :disabled="!!editId" placeholder="邮箱" />
        </el-form-item>
        <el-form-item v-if="!editId" label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" show-password />
        </el-form-item>
        <el-form-item v-if="editId" label="新密码">
          <el-input v-model="form.password" type="password" placeholder="留空则不修改" show-password />
        </el-form-item>
        <el-form-item label="姓名" prop="full_name">
          <el-input v-model="form.full_name" placeholder="姓名" />
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
import { users as usersApi } from '../api'

const list = ref([])
const dialogVisible = ref(false)
const editId = ref(null)
const loading = ref(false)
const formRef = ref()
const form = reactive({ username: '', email: '', password: '', full_name: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名' }],
  email: [{ required: true, message: '请输入邮箱' }, { type: 'email', message: '邮箱格式不正确' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const load = async () => {
  list.value = await usersApi.listTA()
}

const showDialog = (row) => {
  editId.value = row?.id || null
  form.username = row?.username || ''
  form.email = row?.email || ''
  form.password = ''
  form.full_name = row?.full_name || ''
  dialogVisible.value = true
}

const onSubmit = async () => {
  if (!editId.value && !form.password) {
    ElMessage.warning('请填写密码')
    return
  }
  loading.value = true
  try {
    if (editId.value) {
      await usersApi.updateTA(editId.value, {
        full_name: form.full_name,
        ...(form.password ? { password: form.password } : {}),
      })
      ElMessage.success('已更新')
    } else {
      await formRef.value?.validate()
      await usersApi.createTA(form)
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

const onDelete = async (row) => {
  await ElMessageBox.confirm('确定删除该助教？', '提示', { type: 'warning' })
  await usersApi.deleteTA(row.id)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<template>
  <div class="reset-page">
    <div class="login-bg">
      <div class="gradient-orb orb-1"></div>
    </div>
    <div class="reset-card">
      <div class="login-header">
        <h1>重置密码</h1>
        <p>输入新密码</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules">
        <el-form-item v-if="!tokenFromQuery" label="重置 Token" prop="token">
          <el-input v-model="form.token" placeholder="从忘记密码页面获取的 token" />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="form.new_password" type="password" placeholder="新密码" size="large" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" class="login-btn" @click="onSubmit">
            重置密码
          </el-button>
        </el-form-item>
      </el-form>
      <div class="login-links">
        <router-link to="/login">返回登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { auth as authApi } from '../api'

const route = useRoute()
const router = useRouter()
const tokenFromQuery = computed(() => !!route.query.token)
const formRef = ref()
const loading = ref(false)
const form = reactive({
  token: (route.query.token || '') + '',
  new_password: '',
})
const rules = computed(() => ({
  token: tokenFromQuery.value ? [] : [{ required: true, message: '请输入 token' }],
  new_password: [{ required: true, message: '请输入新密码' }, { min: 6, message: '密码至少6位' }],
}))

const onSubmit = async () => {
  if (tokenFromQuery.value) form.token = route.query.token
  await formRef.value?.validate()
  loading.value = true
  try {
    await authApi.resetPassword({ token: form.token, new_password: form.new_password })
    ElMessage.success('密码已重置，请登录')
    router.push('/login')
  } catch (e) {
    ElMessage.error(e.detail || e.message || '重置失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.reset-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
  position: relative;
}
.login-bg { position: absolute; inset: 0; overflow: hidden; }
.gradient-orb {
  position: absolute;
  width: 400px; height: 400px;
  background: #667eea;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.5;
  top: -100px; right: -100px;
}
.reset-card {
  position: relative;
  width: 420px;
  padding: 48px 40px;
  background: rgba(255,255,255,0.95);
  border-radius: 16px;
  box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
}
.login-header { text-align: center; margin-bottom: 32px; }
.login-header h1 { font-size: 24px; color: #1a1d29; margin-bottom: 8px; }
.login-header p { color: #64748b; font-size: 14px; }
.login-btn { width: 100%; height: 44px; border-radius: 8px; }
.login-links { text-align: center; margin-top: 16px; }
.login-links a { color: #667eea; text-decoration: none; }
</style>

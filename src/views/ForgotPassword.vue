<template>
  <div class="forgot-page">
    <div class="login-bg">
      <div class="gradient-orb orb-1"></div>
    </div>
    <div class="forgot-card">
      <div class="login-header">
        <h1>忘记密码</h1>
        <p>输入注册邮箱，我们将发送重置链接（演示模式会返回 token）</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules">
        <el-form-item prop="email">
          <el-input v-model="form.email" placeholder="注册邮箱" size="large" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" class="login-btn" @click="onSubmit">
            发送重置链接
          </el-button>
        </el-form-item>
      </el-form>
      <div v-if="resetToken" class="reset-token">
        <p>演示模式：请使用以下 token 重置密码</p>
        <el-input v-model="resetToken" readonly />
        <router-link :to="`/reset-password?token=${resetToken}`">前往重置密码</router-link>
      </div>
      <div class="login-links">
        <router-link to="/login">返回登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { auth as authApi } from '../api'

const formRef = ref()
const loading = ref(false)
const resetToken = ref('')
const form = reactive({ email: '' })
const rules = { email: [{ required: true, message: '请输入邮箱' }, { type: 'email', message: '邮箱格式不正确' }] }

const onSubmit = async () => {
  await formRef.value?.validate()
  loading.value = true
  resetToken.value = ''
  try {
    const res = await authApi.forgotPassword(form)
    ElMessage.success(res.message || '已发送')
    if (res.reset_token) resetToken.value = res.reset_token
  } catch (e) {
    ElMessage.error(e.detail || e.message || '操作失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.forgot-page {
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
.forgot-card {
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
.reset-token { margin-top: 16px; padding: 16px; background: #f8fafc; border-radius: 8px; }
.reset-token p { margin-bottom: 8px; font-size: 12px; color: #64748b; }
.login-links { text-align: center; margin-top: 16px; }
.login-links a { color: #667eea; text-decoration: none; }
</style>

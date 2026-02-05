<template>
  <div class="login-page">
    <div class="login-bg">
      <div class="gradient-orb orb-1"></div>
      <div class="gradient-orb orb-2"></div>
      <div class="gradient-orb orb-3"></div>
    </div>
    <div class="login-card">
      <div class="login-header">
        <h1>RAG 学习管理系统</h1>
        <p>登录您的账户</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" class="login-form">
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            size="large"
            :prefix-icon="User"
            @keyup.enter="onSubmit"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            show-password
            :prefix-icon="Lock"
            @keyup.enter="onSubmit"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" class="login-btn" @click="onSubmit">
            登 录
          </el-button>
        </el-form-item>
      </el-form>
      <div class="login-links">
        <router-link to="/register">学生注册</router-link>
        <span>|</span>
        <router-link to="/forgot-password">忘记密码</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { User, Lock } from '@element-plus/icons-vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { auth as authApi } from '../api'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const formRef = ref()
const loading = ref(false)
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名' }],
  password: [{ required: true, message: '请输入密码' }],
}

const onSubmit = async () => {
  await formRef.value?.validate()
  loading.value = true
  try {
    const { access_token, user } = await authApi.login(form)
    auth.setAuth(access_token, user)
    ElMessage.success('登录成功')
    router.push(route.query.redirect || '/')
  } catch (e) {
    ElMessage.error(e.detail || e.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
  position: relative;
  overflow: hidden;
}
.login-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
}
.gradient-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.5;
}
.orb-1 { width: 400px; height: 400px; background: #667eea; top: -100px; right: -100px; }
.orb-2 { width: 300px; height: 300px; background: #764ba2; bottom: -50px; left: -50px; }
.orb-3 { width: 200px; height: 200px; background: #f093fb; top: 50%; left: 20%; opacity: 0.3; }
.login-card {
  position: relative;
  width: 420px;
  padding: 48px 40px;
  background: rgba(255,255,255,0.95);
  border-radius: 16px;
  box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
}
.login-header {
  text-align: center;
  margin-bottom: 32px;
}
.login-header h1 {
  font-size: 24px;
  color: #1a1d29;
  margin-bottom: 8px;
}
.login-header p {
  color: #64748b;
  font-size: 14px;
}
.login-form :deep(.el-input__wrapper) { border-radius: 8px; }
.login-btn { width: 100%; height: 44px; border-radius: 8px; }
.login-links {
  text-align: center;
  margin-top: 16px;
  font-size: 14px;
  color: #64748b;
}
.login-links a {
  color: #667eea;
  text-decoration: none;
  margin: 0 8px;
}
.login-links a:hover { text-decoration: underline; }
</style>

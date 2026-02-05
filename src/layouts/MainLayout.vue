<template>
  <el-container class="main-layout">
    <el-aside width="240px" class="sidebar">
      <div class="logo">RAG 学习管理系统</div>
      <el-menu
        :default-active="$route.path"
        router
        class="sidebar-menu"
        background-color="#1a1d29"
        text-color="#a0aec0"
        active-text-color="#667eea"
      >
        <el-menu-item index="/">
          <el-icon><Odometer /></el-icon>
          <span>概览</span>
        </el-menu-item>
        <el-menu-item v-if="auth.canManageTA" index="/users">
          <el-icon><User /></el-icon>
          <span>助教管理</span>
        </el-menu-item>
        <el-menu-item index="/models">
          <el-icon><Cpu /></el-icon>
          <span>模型配置</span>
        </el-menu-item>
        <el-menu-item index="/knowledge">
          <el-icon><Document /></el-icon>
          <span>知识库 RAG</span>
        </el-menu-item>
        <el-menu-item index="/prompts">
          <el-icon><Edit /></el-icon>
          <span>Prompt 配置</span>
        </el-menu-item>
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>对话测试</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span class="header-title">{{ $route.meta.title || 'RAG 学习管理系统' }}</span>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-dropdown">
              <el-icon><User /></el-icon>
              {{ auth.user?.username }} ({{ roleLabel }})
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <keep-alive :include="['Chat']">
              <component :is="Component" />
            </keep-alive>
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

const roleLabel = { teacher: '教师', ta: '助教', student: '学生' }[auth.user?.role] || ''

const handleCommand = (cmd) => {
  if (cmd === 'logout') {
    auth.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.main-layout { height: 100vh; }
.sidebar {
  background: #1a1d29;
  color: #a0aec0;
}
.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  border-bottom: 1px solid #2d3748;
}
.sidebar-menu { border-right: none; }
.header {
  background: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}
.header-title { font-size: 18px; font-weight: 500; }
.header-right { display: flex; align-items: center; }
.user-dropdown {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: #333;
}
.main-content {
  background: #f5f7fa;
  padding: 24px;
  overflow-y: auto;
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>

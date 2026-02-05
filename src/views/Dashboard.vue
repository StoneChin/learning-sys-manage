<template>
  <div class="dashboard">
    <h2>欢迎使用 RAG 学习管理系统</h2>
    <el-row :gutter="24" class="stats">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #ecfdf5; color: #059669;"><el-icon><Document /></el-icon></div>
          <div class="stat-value">{{ stats.kbs }}</div>
          <div class="stat-label">知识库</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #eff6ff; color: #2563eb;"><el-icon><Cpu /></el-icon></div>
          <div class="stat-value">{{ stats.models }}</div>
          <div class="stat-label">模型配置</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #fdf4ff; color: #9333ea;"><el-icon><Edit /></el-icon></div>
          <div class="stat-value">{{ stats.prompts }}</div>
          <div class="stat-label">Prompt 配置</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #fff7ed; color: #ea580c;"><el-icon><ChatDotRound /></el-icon></div>
          <div class="stat-value">—</div>
          <div class="stat-label">对话测试</div>
        </el-card>
      </el-col>
    </el-row>
    <el-card class="quick-links">
      <template #header>快速入口</template>
      <el-space wrap>
        <el-button type="primary" @click="$router.push('/models')">配置模型</el-button>
        <el-button @click="$router.push('/knowledge')">管理知识库</el-button>
        <el-button @click="$router.push('/prompts')">自定义 Prompt</el-button>
        <el-button @click="$router.push('/chat')">对话测试</el-button>
      </el-space>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { knowledge, models, prompts } from '../api'

const stats = ref({ kbs: 0, models: 0, prompts: 0 })

onMounted(async () => {
  try {
    const [k, m, p] = await Promise.all([knowledge.list(), models.list(), prompts.list()])
    stats.value = { kbs: k.length, models: m.length, prompts: p.length }
  } catch (_) {}
})
</script>

<style scoped>
.dashboard h2 { margin-bottom: 24px; color: #1a1d29; }
.stats { margin-bottom: 24px; }
.stat-card { text-align: center; }
.stat-icon {
  width: 48px; height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 12px;
  font-size: 24px;
}
.stat-value { font-size: 28px; font-weight: 600; color: #1a1d29; }
.stat-label { color: #64748b; font-size: 14px; margin-top: 4px; }
</style>

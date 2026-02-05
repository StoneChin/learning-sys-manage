<template>
  <div class="chat-page">
    <el-card>
      <template #header>
        <span>对话测试</span>
        <div class="chat-options">
          <el-select v-model="modelConfigId" placeholder="选择模型" style="width: 180px; margin-right: 12px" clearable>
            <el-option v-for="m in modelList" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
          <el-select v-model="kbId" placeholder="选择知识库(RAG)" style="width: 180px; margin-right: 12px" clearable>
            <el-option v-for="k in kbList" :key="k.id" :label="k.name" :value="k.id" />
          </el-select>
          <el-select v-model="promptConfigId" placeholder="选择 Prompt" style="width: 200px" clearable>
            <el-option v-for="p in promptList" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </div>
      </template>
      <div class="chat-area">
        <div ref="messagesRef" class="messages">
          <div v-for="(msg, i) in messages" :key="i" :class="['msg', msg.role]">
            <span class="role">{{ msg.role === 'user' ? '我' : '助手' }}</span>
            <span class="content">{{ msg.content }}</span>
          </div>
          <div v-if="loading" class="msg assistant">
            <span class="role">助手</span>
            <span class="content typing">{{ streamingContent || '正在思考...' }}</span>
          </div>
        </div>
        <div class="input-area">
          <el-input
            v-model="input"
            type="textarea"
            :rows="3"
            placeholder="输入消息，按 Ctrl+Enter 发送"
            @keydown.ctrl.enter="send"
          />
          <el-button type="primary" :loading="loading" @click="send">发送</el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onActivated, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { chat as chatApi, models, knowledge, prompts } from '../api'

defineOptions({ name: 'Chat' })

const messages = ref([])
const input = ref('')
const loading = ref(false)
const streamingContent = ref('')
const modelConfigId = ref(null)
const kbId = ref(null)
const promptConfigId = ref(null)
const modelList = ref([])
const kbList = ref([])
const promptList = ref([])
const messagesRef = ref()

const refreshOptions = async () => {
  try {
    const [m, k, p] = await Promise.all([models.list(), knowledge.list(), prompts.list()])
    modelList.value = m
    kbList.value = k
    promptList.value = p
    if (m.length && !modelConfigId.value) {
      const def = m.find((x) => x.is_default) || m[0]
      modelConfigId.value = def.id
    }
    if (p.length && !promptConfigId.value) {
      const def = p.find((x) => x.is_default) || p[0]
      promptConfigId.value = def?.id ?? null
    }
  } catch (_) {}
}

const send = async () => {
  const text = input.value?.trim()
  if (!text || loading.value) return
  messages.value.push({ role: 'user', content: text })
  input.value = ''
  loading.value = true
  streamingContent.value = ''
  try {
    const payload = {
      messages: messages.value.map((m) => ({ role: m.role, content: m.content })),
      model_config_id: modelConfigId.value || undefined,
      kb_id: kbId.value || undefined,
      prompt_config_id: promptConfigId.value || undefined,
    }
    await chatApi.completionsStream(payload, (chunk) => {
      streamingContent.value += chunk
      nextTick(() => messagesRef.value?.scrollTo?.({ top: messagesRef.value.scrollHeight }))
    })
    messages.value.push({ role: 'assistant', content: streamingContent.value })
    streamingContent.value = ''
    await nextTick()
    messagesRef.value?.scrollTo?.({ top: messagesRef.value.scrollHeight })
  } catch (e) {
    ElMessage.error(e.message || e.detail || '请求失败')
    messages.value.pop()
  } finally {
    loading.value = false
  }
}

onMounted(refreshOptions)
onActivated(refreshOptions)
</script>

<style scoped>
.chat-options {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.chat-area {
  min-height: 400px;
  display: flex;
  flex-direction: column;
}
.messages {
  flex: 1;
  max-height: 480px;
  overflow-y: auto;
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
  margin-bottom: 16px;
}
.msg {
  margin-bottom: 16px;
}
.msg.user { text-align: right; }
.msg .role {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
  display: block;
}
.msg .content {
  display: inline-block;
  padding: 10px 14px;
  border-radius: 8px;
  max-width: 80%;
  white-space: pre-wrap;
}
.msg.user .content { background: #667eea; color: #fff; }
.msg.assistant .content { background: #fff; border: 1px solid #e2e8f0; }
.msg .content.typing { color: #64748b; }
.input-area {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
.input-area .el-input { flex: 1; }
</style>

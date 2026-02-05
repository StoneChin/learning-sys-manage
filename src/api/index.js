import request from './request'

const auth = {
  login: (data) => request.post('/api/auth/login', data),
  register: (data) => request.post('/api/auth/register', data),
  forgotPassword: (data) => request.post('/api/auth/forgot-password', data),
  resetPassword: (data) => request.post('/api/auth/reset-password', data),
  me: () => request.get('/api/auth/me'),
}

const users = {
  list: () => request.get('/api/users/ta'),
  create: (data) => request.post('/api/users/ta', data),
  update: (id, data) => request.patch(`/api/users/ta/${id}`, data),
  delete: (id) => request.delete(`/api/users/ta/${id}`),
}

const models = {
  list: () => request.get('/api/models'),
  localList: () => request.get('/api/models/local-list'),
  modelscopeList: () => request.get('/api/models/modelscope-list'),
  modelscopeDownload: (modelId, saveDir) =>
    request.post('/api/models/modelscope-download', null, { params: { model_id: modelId, save_dir: saveDir } }),
  create: (data) => request.post('/api/models', data),
  update: (id, data) => request.patch(`/api/models/${id}`, data),
  delete: (id) => request.delete(`/api/models/${id}`),
}

const knowledge = {
  list: () => request.get('/api/knowledge'),
  create: (data) => request.post('/api/knowledge', data),
  update: (id, data) => request.patch(`/api/knowledge/${id}`, data),
  delete: (id) => request.delete(`/api/knowledge/${id}`),
  getStatus: (kbId) => request.get(`/api/knowledge/${kbId}/status`),
  listDocuments: (kbId) => request.get(`/api/knowledge/${kbId}/documents`),
  upload: (kbId, file) => {
    const form = new FormData()
    form.append('file', file)
    return request.post(`/api/knowledge/${kbId}/upload`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  build: (kbId) => request.post(`/api/knowledge/${kbId}/build`),
  deleteDocument: (kbId, docId) => request.delete(`/api/knowledge/${kbId}/documents/${docId}`),
  getRagConfig: () => request.get('/api/knowledge/rag-config'),
  updateRagConfig: (data) => request.patch('/api/knowledge/rag-config', data),
  getGraph: (kbId, limit = 500) => request.get(`/api/knowledge/${kbId}/graph`, { params: { limit } }),
  getNodes: (kbId, keyword, limit = 50) =>
    request.get(`/api/knowledge/${kbId}/nodes`, { params: { keyword: keyword || undefined, limit } }),
  getPath: (kbId, fromName, toName, maxDepth = 10) =>
    request.get(`/api/knowledge/${kbId}/path`, {
      params: { from_name: fromName, to_name: toName, max_depth: maxDepth },
    }),
}

const prompts = {
  list: () => request.get('/api/prompts'),
  create: (data) => request.post('/api/prompts', data),
  update: (id, data) => request.patch(`/api/prompts/${id}`, data),
  delete: (id) => request.delete(`/api/prompts/${id}`),
}

async function completionsStream(payload, onChunk) {
  const token = localStorage.getItem('token')
  const res = await fetch('/api/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: token ? `Bearer ${token}` : '',
    },
    body: JSON.stringify({ ...payload, stream: true }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || err.message || '请求失败')
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const lines = buf.split('\n')
    buf = lines.pop() || ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const raw = line.slice(6)
        if (raw === '[DONE]') return
        try {
          const obj = JSON.parse(raw)
          if (obj.error) throw new Error(obj.error)
          const content = obj.choices?.[0]?.delta?.content
          if (content && onChunk) onChunk(content)
        } catch (e) {
          if (e instanceof SyntaxError) continue
          throw e
        }
      }
    }
  }
}

const chat = {
  completions: (payload) => request.post('/api/chat/completions', payload),
  completionsStream,
  search: (kbId, query, topK = 5) =>
    request.post('/api/chat/search', null, { params: { kb_id: kbId, query, top_k: topK } }),
}

export { auth, users, models, knowledge, prompts, chat }

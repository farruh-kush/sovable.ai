import axios from 'axios'
const configuredBase = process.env.NEXT_PUBLIC_API_BASE_URL || '/v1'
export const api = axios.create({ baseURL: configuredBase, headers: { 'Content-Type': 'application/json' } })
function browserValue(key: string) { return typeof window === 'undefined' ? '' : window.localStorage.getItem(key) || '' }
api.interceptors.request.use((config) => {
  const apiKey = browserValue('solvable_api_key'), adminKey = browserValue('solvable_admin_key')
  if (config.headers) { if (config.url?.includes('/keys') || config.url?.includes('/admin')) { if (adminKey) config.headers['x-admin-key'] = adminKey } else if (apiKey) config.headers.Authorization = `Bearer ${apiKey}` }
  return config
})
export async function getHealth() { const root = configuredBase.replace(/\/v1\/?$/, '') || '/'; return (await axios.get(`${root}/health`)).data }
export async function getModels() { return (await api.get('/models')).data }
export async function listKeys() { return (await api.get('/keys')).data }
export async function createKey(name: string, tier = 'free') { return (await api.post('/keys', { name, tier })).data }
export async function chatCompletion(payload: Record<string, unknown>) { return (await api.post('/chat/completions', payload)).data }
export async function getAdminOverview() { return (await api.get('/admin/overview')).data }
export default api

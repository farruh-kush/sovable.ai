import axios from 'axios'

const api = axios.create({
  baseURL: '/v1',
  headers: {
    // default developer key for local dev; can be overridden by callers
    Authorization: 'Bearer dev-default-key',
    'Content-Type': 'application/json'
  }
})

export async function getHealth(){
  const r = await api.get('/health')
  return r.data
}

export async function listKeys(){
  try{
    const r = await api.get('/keys')
    return r.data
  }catch(e){
    return {error: true, message: 'Unable to fetch keys'}
  }
}

export async function createKey(name:string){
  const r = await api.post('/keys', {name})
  return r.data
}

export async function chatCompletion(payload:any){
  const r = await api.post('/chat/completions', payload)
  return r.data
}

export default api

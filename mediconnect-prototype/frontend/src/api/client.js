import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8002'

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

client.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const api = {
  login: (username, password) => client.post('/auth/login', { username, password }),
  getMe: () => client.get('/auth/me'),
  
  appointments: {
    create: (data) => client.post('/appointments', data),
    list: () => client.get('/appointments'),
    get: (id) => client.get(`/appointments/${id}`),
    update: (id, data) => client.put(`/appointments/${id}`, data),
    delete: (id) => client.delete(`/appointments/${id}`)
  }
}

export default client
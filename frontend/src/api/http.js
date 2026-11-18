import axios from 'axios'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api',
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config || {}
    if (error.response?.status === 401 && !original._retry) {
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        original._retry = true
        try {
          const response = await axios.post(`${http.defaults.baseURL}/token/refresh/`, { refresh })
          localStorage.setItem('access_token', response.data.access)
          original.headers.Authorization = `Bearer ${response.data.access}`
          return http(original)
        } catch {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.dispatchEvent(new CustomEvent('matflow-auth-expired'))
        }
      }
    }
    return Promise.reject(error)
  },
)

export default http

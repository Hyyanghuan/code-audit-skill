import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

export default api

export function downloadUrl(jobId, filename, format) {
  const token = localStorage.getItem('token')
  return `/api/audits/${jobId}/documents/${encodeURIComponent(filename)}/download?format=${format}&token=${token}`
}

export async function downloadFile(jobId, filename, format) {
  const resp = await api.get(
    `/audits/${jobId}/documents/${encodeURIComponent(filename)}/download`,
    { params: { format }, responseType: 'blob' }
  )
  const cd = resp.headers['content-disposition'] || ''
  const match = cd.match(/filename="([^"]+)"/)
  const outName = match ? match[1] : `${filename}.${format}`
  const url = URL.createObjectURL(resp.data)
  const a = document.createElement('a')
  a.href = url
  a.download = outName
  a.click()
  URL.revokeObjectURL(url)
}

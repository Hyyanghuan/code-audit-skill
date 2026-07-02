import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'

export default function Login() {
  const nav = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await api.post('/auth/login', { username, password })
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('username', data.username)
      nav('/')
    } catch (err) {
      setError(err.response?.data?.detail || '登录失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-box card">
        <h2>Code Audit Console</h2>
        <p className="hint">使用分配的账户登录（无找回/重置密码入口）</p>
        {error && <div className="error">{error}</div>}
        <form onSubmit={submit}>
          <label>邮箱 / 用户名</label>
          <input
            type="email"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="2634564881@qq.com"
            required
          />
          <label>密码</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button className="btn" type="submit" disabled={loading} style={{ width: '100%' }}>
            {loading ? '登录中…' : '登录'}
          </button>
        </form>
      </div>
    </div>
  )
}

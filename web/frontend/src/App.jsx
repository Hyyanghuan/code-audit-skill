import { useEffect, useState } from 'react'

import { Navigate, Route, Routes, Link, useLocation, useNavigate } from 'react-router-dom'

import Login from './pages/Login'

import Dashboard from './pages/Dashboard'

import AuditNew from './pages/AuditNew'

import JobDetail from './pages/JobDetail'

import ExecutionReport from './pages/ExecutionReport'

import Settings from './pages/Settings'

import api from './api'



function RequireAuth({ children }) {

  const token = localStorage.getItem('token')

  if (!token) return <Navigate to="/login" replace />

  return children

}



function Layout({ children }) {

  const loc = useLocation()

  const nav = useNavigate()

  const [username, setUsername] = useState(localStorage.getItem('username') || '')



  useEffect(() => {

    api.get('/auth/me')

      .then(({ data }) => {

        setUsername(data.username)

        localStorage.setItem('username', data.username)

      })

      .catch(() => {})

  }, [])



  const logout = () => {

    localStorage.removeItem('token')

    localStorage.removeItem('githubToken')

    localStorage.removeItem('username')

    nav('/login')

  }

  const isActive = (path) => (loc.pathname === path ? 'active' : '')

  const wide = loc.pathname.startsWith('/jobs/') || loc.pathname.startsWith('/reports') || loc.pathname.startsWith('/bugs')



  return (

    <div className="layout">

      <aside className="sidebar">

        <h1>Code Audit</h1>

        <nav>

          <Link to="/" className={isActive('/')}>任务列表</Link>

          <Link to="/reports" className={isActive('/reports') || isActive('/bugs') ? 'active' : ''}>审计执行报告</Link>

          <Link to="/audit/new" className={isActive('/audit/new')}>新建审计</Link>

          <Link to="/settings" className={isActive('/settings')}>系统配置</Link>

        </nav>

        <div className="sidebar-footer">

          <div className="sidebar-user">

            <span className="user-label">当前用户</span>

            <span className="user-name">{username || '…'}</span>

          </div>

          <button type="button" className="btn secondary sm sidebar-logout" onClick={logout}>

            退出登录

          </button>

        </div>

      </aside>

      <main className={`main ${wide ? 'main-wide' : ''}`}>{children}</main>

    </div>

  )

}



export default function App() {

  return (

    <Routes>

      <Route path="/login" element={<Login />} />

      <Route

        path="/*"

        element={

          <RequireAuth>

            <Layout>

              <Routes>

                <Route path="/" element={<Dashboard />} />

                <Route path="/reports" element={<ExecutionReport />} />
                <Route path="/bugs" element={<ExecutionReport />} />

                <Route path="/audit/new" element={<AuditNew />} />

                <Route path="/jobs/:jobId" element={<JobDetail />} />

                <Route path="/settings" element={<Settings />} />

              </Routes>

            </Layout>

          </RequireAuth>

        }

      />

    </Routes>

  )

}


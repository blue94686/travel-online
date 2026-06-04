import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, CheckCircle, Lock, Mail } from 'lucide-react'
import HeroSection from '../components/common/HeroSection.jsx'
import { useAuth } from '../hooks/useAuth.jsx'
import './AuthV2.css'

export default function AuthPage() {
  const navigate = useNavigate()
  const { login, register, sendCode, isLoggedIn, isAdmin } = useAuth()
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [countdown, setCountdown] = useState(0)

  useEffect(() => {
    if (countdown <= 0) return undefined
    const timer = setTimeout(() => setCountdown(countdown - 1), 1000)
    return () => clearTimeout(timer)
  }, [countdown])

  useEffect(() => {
    if (isLoggedIn) navigate(isAdmin ? '/admin' : '/user', { replace: true })
  }, [isLoggedIn, isAdmin, navigate])

  const handleSendCode = async () => {
    if (!email.includes('@')) {
      setNotice('')
      setError('请输入有效邮箱')
      return
    }
    setError('')
    setNotice('')
    const result = await sendCode(email)
    if (result.success) {
      setNotice(result.message || '验证码已发送')
      setCountdown(60)
    } else {
      setError(result.error || '验证码发送失败')
    }
  }

  const submit = async (event) => {
    event.preventDefault()
    if (!email.includes('@')) return setError('请输入有效邮箱')
    if (password.length < 6) return setError('请输入至少6位密码')
    if (mode === 'register' && !/^\d{6}$/.test(code)) return setError('请输入6位验证码')

    setSubmitting(true)
    setError('')
    setNotice('')
    const result = mode === 'login' ? await login(email, password) : await register(email, password, code)
    setSubmitting(false)

    if (result.success) {
      const role = result.user?.role || 'user'
      navigate(role === 'user' ? '/user' : '/admin')
    } else {
      setError(result.error || (mode === 'login' ? '账号或密码错误' : '注册失败'))
    }
  }

  return (
    <HeroSection
      variant="split"
      title="账号登录"
      subtitle="登录使用邮箱账号和密码，注册需要邮箱验证码"
      image="https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=1600&q=80"
    >
      <div className="auth-card-container auth-card-simple">
        <form className="auth-form-v2" onSubmit={submit}>
          <div className="auth-form-content">
            <div className="auth-tabs-v2" role="tablist" aria-label="认证方式">
              <button
                type="button"
                className={mode === 'login' ? 'active' : ''}
                aria-pressed={mode === 'login'}
                onClick={() => { setMode('login'); setError(''); setNotice('') }}
              >
                登录
              </button>
              <button
                type="button"
                className={mode === 'register' ? 'active' : ''}
                aria-pressed={mode === 'register'}
                onClick={() => { setMode('register'); setError(''); setNotice('') }}
              >
                注册
              </button>
            </div>

            <h2>{mode === 'login' ? '账号密码登录' : '账号密码注册'}</h2>
            <p className="auth-subtitle">{mode === 'login' ? '输入邮箱和密码即可进入。' : '输入邮箱、密码和验证码创建账号。'}</p>

            {error && <div className="auth-alert danger"><AlertCircle size={16} /> {error}</div>}
            {notice && <div className="auth-alert success"><CheckCircle size={16} /> {notice}</div>}

            <div className="auth-input-group">
              <label>邮箱</label>
              <div className="input-wrapper">
                <Mail size={18} className="input-icon" />
                <input
                  type="email"
                  value={email}
                  onChange={event => setEmail(event.target.value)}
                  placeholder="请输入邮箱地址"
                  required
                />
              </div>
            </div>

            <div className="auth-input-group">
              <label>密码</label>
              <div className="input-wrapper">
                <Lock size={18} className="input-icon" />
                <input
                  type="password"
                  value={password}
                  onChange={event => setPassword(event.target.value)}
                  placeholder="请输入密码"
                  required
                  minLength={6}
                />
              </div>
            </div>

            {mode === 'register' && (
              <div className="auth-input-group">
                <label>验证码</label>
                <div className="input-wrapper with-action">
                  <Lock size={18} className="input-icon" />
                  <input
                    inputMode="numeric"
                    value={code}
                    onChange={event => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="请输入6位验证码"
                    required
                    maxLength={6}
                  />
                  <button
                    type="button"
                    className="send-code-btn"
                    onClick={handleSendCode}
                    disabled={countdown > 0}
                  >
                    {countdown > 0 ? `${countdown}s` : '发送验证码'}
                  </button>
                </div>
              </div>
            )}

            <button className="auth-submit-btn" disabled={submitting}>
              {submitting ? '处理中...' : (mode === 'login' ? '登录' : '注册')}
            </button>
          </div>
        </form>
      </div>
    </HeroSection>
  )
}

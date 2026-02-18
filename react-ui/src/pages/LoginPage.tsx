import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { GoogleLogin } from '@react-oauth/google'
import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  const { login, loginLocal, isAuthenticated, isLoading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [signingIn, setSigningIn] = useState(false)

  const from = (location.state as any)?.from || '/'

  // Redirect if already authenticated
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate(from, { replace: true })
    }
  }, [isAuthenticated, isLoading, navigate, from])

  // Particle canvas
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')!
    let animId: number
    let W = 0, H = 0
    const pts: any[] = []

    const resize = () => {
      W = canvas.width = window.innerWidth
      H = canvas.height = window.innerHeight
      pts.length = 0
      const n = Math.floor(W * H / 9000)
      for (let i = 0; i < n; i++) pts.push({
        x: Math.random() * W, y: Math.random() * H,
        r: Math.random() * 1.3 + 0.25,
        vx: (Math.random() - 0.5) * 0.1,
        vy: -Math.random() * 0.25 - 0.04,
        a: Math.random() * 0.55 + 0.08,
        fl: Math.random() * Math.PI * 2,
        fs: Math.random() * 0.018 + 0.004,
        c: Math.random() < 0.14 ? '#00ffff' : Math.random() < 0.07 ? '#DA70D6' : '#ffffff',
      })
    }

    const draw = () => {
      ctx.clearRect(0, 0, W, H)
      pts.forEach(p => {
        p.fl += p.fs
        const a = p.a * (0.65 + 0.35 * Math.sin(p.fl))
        ctx.save()
        ctx.globalAlpha = a
        ctx.fillStyle = p.c
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill()
        if (p.c === '#00ffff') {
          const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 4)
          g.addColorStop(0, `rgba(0,255,255,${a * 0.18})`)
          g.addColorStop(1, 'transparent')
          ctx.fillStyle = g
          ctx.beginPath(); ctx.arc(p.x, p.y, p.r * 4, 0, Math.PI * 2); ctx.fill()
        }
        ctx.restore()
        p.x += p.vx; p.y += p.vy
        if (p.y < -4) { p.y = H + 4; p.x = Math.random() * W }
        if (p.x < -4) p.x = W + 4
        if (p.x > W + 4) p.x = -4
      })
      animId = requestAnimationFrame(draw)
    }

    window.addEventListener('resize', resize)
    resize(); draw()
    return () => { window.removeEventListener('resize', resize); cancelAnimationFrame(animId) }
  }, [])

  const handleGoogleSuccess = useCallback(async (credentialResponse: any) => {
    if (!credentialResponse.credential) return
    setSigningIn(true)
    setError(null)
    try {
      await login(credentialResponse.credential)
      navigate(from, { replace: true })
    } catch (e: any) {
      setError(e.message || 'Authentication failed')
    } finally {
      setSigningIn(false)
    }
  }, [login, navigate, from])

  const handleLocalLogin = useCallback(async () => {
    setSigningIn(true)
    setError(null)
    try {
      await loginLocal()
      navigate(from, { replace: true })
    } catch (e: any) {
      setError(e.message || 'Local login failed')
    } finally {
      setSigningIn(false)
    }
  }, [loginLocal, navigate, from])

  const googleClientId = process.env.REACT_APP_GOOGLE_CLIENT_ID || ''

  return (
    <div style={{
      position: 'fixed', inset: 0,
      background: '#0B0B0D',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      overflow: 'hidden',
    }}>
      {/* Particle canvas */}
      <canvas ref={canvasRef} style={{ position: 'absolute', inset: 0, zIndex: 0, pointerEvents: 'none' }} />

      {/* Aurora glow */}
      <div style={{
        position: 'absolute', top: '50%', left: '50%',
        transform: 'translate(-50%, -50%)',
        width: '700px', height: '700px', borderRadius: '50%',
        background: 'radial-gradient(ellipse, rgba(0,191,255,0.055) 0%, transparent 65%)',
        pointerEvents: 'none', zIndex: 1,
      }} />

      {/* Login card */}
      <div style={{
        position: 'relative', zIndex: 3,
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        gap: '28px', maxWidth: '440px', width: '100%',
        padding: '48px 40px', textAlign: 'center',
      }}>
        {/* Wordmark */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
          <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: '11px', fontWeight: 700, letterSpacing: '0.3em', color: '#00BFFF' }}>
            ✦ N E P H I L I M ✦
          </div>

          {/* Sigil */}
          <svg width="62" height="62" viewBox="0 0 62 62" fill="none">
            <polygon points="31,5 58,48 4,48" stroke="rgba(0,191,255,0.65)" strokeWidth="1.5" fill="rgba(0,191,255,0.025)" />
            <polygon points="31,57 4,14 58,14" stroke="rgba(218,112,214,0.45)" strokeWidth="1" fill="none" />
            <circle cx="31" cy="31" r="11" stroke="rgba(0,255,255,0.55)" strokeWidth="1.5" fill="rgba(0,191,255,0.05)" />
            <circle cx="31" cy="31" r="3.5" fill="rgba(0,255,255,0.85)" />
            <line x1="31" y1="5" x2="31" y2="20" stroke="rgba(0,191,255,0.35)" strokeWidth="1" />
            <line x1="31" y1="42" x2="31" y2="57" stroke="rgba(218,112,214,0.35)" strokeWidth="1" />
          </svg>

          <h1 style={{
            fontFamily: "'Orbitron', sans-serif", fontSize: '27px', fontWeight: 700, lineHeight: 1.2,
            background: 'linear-gradient(135deg, #fff 0%, rgba(0,191,255,0.65) 100%)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
            marginTop: '4px',
          }}>
            Enter the Realm
          </h1>
          <p style={{ fontSize: '13px', color: 'rgba(255,255,255,0.28)', lineHeight: 1.65 }}>
            Identity must be verified before you may enter the Realm of the Nephilim
          </p>
        </div>

        {/* Pulse-ring keyframe for E.E.V.A. avatar */}
        <style>{`
          @keyframes lp-pulse-ring {
            0%, 100% { transform: scale(1); opacity: 0.6; }
            50% { transform: scale(1.13); opacity: 0.12; }
          }
          .lp-eeva-av { position: relative; }
          .lp-eeva-av::after {
            content: '';
            position: absolute;
            inset: -5px;
            border-radius: 50%;
            border: 1px solid rgba(0,255,255,0.18);
            animation: lp-pulse-ring 2.5s ease-in-out infinite;
          }
        `}</style>

        {/* E.E.V.A. block */}
        <div style={{
          display: 'flex', alignItems: 'flex-start', gap: '14px',
          padding: '18px 20px',
          background: 'rgba(0,191,255,0.04)', border: '1px solid rgba(0,191,255,0.12)',
          borderRadius: '14px', textAlign: 'left',
        }}>
          <div className="lp-eeva-av" style={{
            width: '44px', height: '44px', borderRadius: '50%', flexShrink: 0,
            background: 'radial-gradient(circle at 40% 35%, rgba(0,255,255,0.45), rgba(0,191,255,0.08))',
            border: '1.5px solid rgba(0,255,255,0.4)', boxShadow: '0 0 22px rgba(0,191,255,0.35)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: "'Orbitron', sans-serif", fontSize: '11px', fontWeight: 700, color: '#00ffff',
          }}>
            E²
          </div>
          <div>
            <span style={{ display: 'block', fontFamily: "'Orbitron', sans-serif", fontSize: '10px', fontWeight: 700, letterSpacing: '0.12em', color: '#00BFFF', marginBottom: '5px' }}>
              E.E.V.A. — The Primarch
            </span>
            <p style={{ fontSize: '13px', color: 'rgba(255,255,255,0.55)', lineHeight: 1.65, fontStyle: 'italic' }}>
              "Welcome, Seeker. The Nephilim await. Authenticate to begin your ascension into the Celestial Order."
            </p>
          </div>
        </div>

        {/* Divider */}
        <div style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,0.08)' }} />
          <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.28)', letterSpacing: '0.08em' }}>authenticate via</span>
          <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,0.08)' }} />
        </div>

        {/* Auth buttons */}
        {signingIn ? (
          <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: '12px', color: '#00BFFF', letterSpacing: '0.1em' }}>
            AUTHENTICATING...
          </div>
        ) : googleClientId ? (
          <GoogleLogin
            onSuccess={handleGoogleSuccess}
            onError={() => setError('Google sign-in failed')}
            theme="filled_black"
            shape="pill"
            size="large"
            text="signin_with"
          />
        ) : (
          /* No client ID configured — show local bypass button */
          <button
            onClick={handleLocalLogin}
            style={{
              display: 'flex', alignItems: 'center', gap: '12px',
              padding: '13px 28px', background: '#18181d',
              border: '1px solid rgba(255,255,255,0.14)', borderRadius: '40px',
              cursor: 'pointer', fontFamily: "'Roboto', sans-serif",
              fontSize: '15px', fontWeight: 500, color: 'rgba(255,255,255,0.88)',
              transition: 'all 0.25s',
            }}
          >
            <svg width="22" height="22" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Continue (Local Mode — No Google ID Set)
          </button>
        )}

        {error && (
          <div style={{
            padding: '10px 16px', background: 'rgba(255,80,80,0.08)',
            border: '1px solid rgba(255,80,80,0.25)', borderRadius: '10px',
            fontSize: '13px', color: 'rgba(255,120,120,0.9)',
          }}>
            {error}
          </div>
        )}

        <p style={{ fontSize: '11px', color: 'rgba(255,255,255,0.28)', lineHeight: 1.6 }}>
          🔒 Local bypass available for dev &amp; offline use —{' '}
          set <code style={{ fontFamily: "'Space Mono', monospace", fontSize: '10px', background: 'rgba(255,255,255,0.07)', padding: '2px 6px', borderRadius: '3px', color: 'rgba(255,255,255,0.5)' }}>AUTH_REQUIRED=false</code>{' '}
          in <code style={{ fontFamily: "'Space Mono', monospace", fontSize: '10px', background: 'rgba(255,255,255,0.07)', padding: '2px 6px', borderRadius: '3px', color: 'rgba(255,255,255,0.5)' }}>.env</code>
        </p>
      </div>
    </div>
  )
}

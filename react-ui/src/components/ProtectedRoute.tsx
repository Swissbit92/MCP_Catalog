import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div style={{
        position: 'fixed', inset: 0,
        background: '#0B0B0D',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexDirection: 'column', gap: '24px',
      }}>
        <style>{`
          @keyframes pr-orb { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
          @keyframes pr-core-p {
            0%,100%{transform:scale(1);box-shadow:0 0 22px rgba(0,191,255,.6);}
            50%{transform:scale(1.18);box-shadow:0 0 44px rgba(0,191,255,.9);}
          }
        `}</style>
        {/* Multi-ring orbit loader matching mockup S3 design */}
        <div style={{ position: 'relative', width: '96px', height: '96px' }}>
          {/* Outer ring — cyan top/right */}
          <div style={{
            position: 'absolute', inset: 0, borderRadius: '50%',
            border: '1.5px solid transparent',
            borderTopColor: '#00BFFF', borderRightColor: 'rgba(0,191,255,0.25)',
            animation: 'pr-orb 2.8s linear infinite',
          }} />
          {/* Middle ring — purple bottom/left, reverse */}
          <div style={{
            position: 'absolute', inset: '12px', borderRadius: '50%',
            border: '1.5px solid transparent',
            borderBottomColor: '#DA70D6', borderLeftColor: 'rgba(218,112,214,0.25)',
            animation: 'pr-orb 2.1s linear infinite reverse',
          }} />
          {/* Inner ring — cyan top */}
          <div style={{
            position: 'absolute', inset: '24px', borderRadius: '50%',
            border: '1.5px solid transparent',
            borderTopColor: '#00ffff',
            animation: 'pr-orb 1.5s linear infinite',
          }} />
          {/* Glowing core */}
          <div style={{
            position: 'absolute', inset: '36px', borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(0,255,255,0.45), rgba(0,191,255,0.08))',
            animation: 'pr-core-p 2s ease-in-out infinite',
            boxShadow: '0 0 22px rgba(0,191,255,0.6)',
          }} />
        </div>
        <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: '11px', color: '#00BFFF', letterSpacing: '0.1em' }}>
          VERIFYING IDENTITY...
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  return <>{children}</>
}

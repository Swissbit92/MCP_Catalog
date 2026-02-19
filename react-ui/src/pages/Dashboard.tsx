import React from 'react'
import NephilimBackground from '../components/NephilimBackground'
import { SeekerDashboard } from '../components/nephilim/SeekerDashboard'
import { useAuth } from '../context/AuthContext'

const Dashboard: React.FC = () => {
  const { user } = useAuth()
  const userId = user?.sub || 'default_seeker'

  return (
    <NephilimBackground particles skyline intensity={0.4}>
      <div className="min-h-full">
        <div className="max-w-5xl mx-auto px-4 md:px-6 py-8">
          <h1 className="text-3xl font-nephilim text-nephilim-cyan mb-8 tracking-wider">
            Seeker&apos;s Sanctum
          </h1>
          <SeekerDashboard userId={userId} />
        </div>
      </div>
    </NephilimBackground>
  )
}

export default Dashboard

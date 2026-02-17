import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import CharacterShowcase from '../components/CharacterShowcase';
import styles from '../components/CharacterCard.module.css';

const Home: React.FC = () => {
  const navigate = useNavigate();



  const handlePullCharacter = () => {
    navigate('/select?tab=pull');
  };

  const handleBrowseCollection = () => {
    navigate('/select');
  };

  return (
    <div className="min-h-screen relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Neutral introduction background - rarity theming activates after persona selection */}

      <div className="relative z-10">
        <div className="text-center py-8">
          <h1 className="text-4xl md:text-6xl font-display font-black text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 via-purple-400 to-blue-400 mb-4">
            AI Companions
          </h1>
          <p className="text-xl font-body text-gray-300 max-w-3xl mx-auto mb-8">
            Connect with intelligent AI companions through our gacha-style agent selection system
          </p>
        </div>

        <motion.div
          className={`${styles['pull-button-container']} bg-black/30 backdrop-blur-sm rounded-2xl border border-white/10`}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className={`${styles['pull-instructions']} text-white`}>
            <h2 className="text-2xl font-display font-bold mb-2">Welcome to AI Companions!</h2>
            <p className="font-body text-gray-300">Choose how you'd like to select your agent to start chatting.</p>
          </div>
          <div className="flex flex-col gap-4 items-center w-full max-w-md">
            <motion.button
              className={styles['pull-button']}
              onClick={handlePullCharacter}
              style={{
                background: 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)',
                boxShadow: '0 8px 32px rgba(251, 191, 36, 0.3)'
              }}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              🎲 Try Your Luck - Gacha Pull
            </motion.button>
            <motion.button
              className={styles['pull-button']}
              onClick={handleBrowseCollection}
              style={{
                background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                boxShadow: '0 8px 32px rgba(245, 158, 11, 0.3)'
              }}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              📚 Browse All Agents
            </motion.button>
          </div>
        </motion.div>

        {/* AI Companion Showcase */}
        <div className="mt-12">
          <h2 className="text-2xl font-display font-bold text-white text-center mb-6">
            AI Companion Showcase
          </h2>
          <CharacterShowcase />
        </div>
      </div>
    </div>
  );
};

export default Home;
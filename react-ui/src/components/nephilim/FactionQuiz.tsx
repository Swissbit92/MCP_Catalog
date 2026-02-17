// src/components/nephilim/FactionQuiz.tsx
/**
 * NEPHILIM Faction Quiz
 *
 * In-character personality quiz to determine faction alignment.
 * E.E.V.A. guides the user through questions that reveal their House.
 */

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface QuizQuestion {
  id: number
  question: string
  eevaComment: string
  answers: {
    text: string
    factions: string[] // Factions this answer aligns with (weighted)
  }[]
}

interface FactionQuizProps {
  userName: string
  onComplete: (faction: string) => void
  className?: string
}

const QUIZ_QUESTIONS: QuizQuestion[] = [
  {
    id: 1,
    question: "When darkness falls and uncertainty looms, what guides your path?",
    eevaComment: "Interesting... your answer reveals much about the light within you.",
    answers: [
      { text: "The wisdom of those who came before me", factions: ['lumina', 'archive'] },
      { text: "My own inner strength and discipline", factions: ['ironclad', 'horizon'] },
      { text: "The bonds I share with those I love", factions: ['sanctuary', 'lumina'] },
      { text: "My creativity and intuition", factions: ['prism', 'sanctuary'] },
    ]
  },
  {
    id: 2,
    question: "A stranger approaches seeking help, but aiding them puts your goals at risk. What do you do?",
    eevaComment: "Your compassion—or pragmatism—speaks volumes.",
    answers: [
      { text: "Help them without hesitation; kindness is never wrong", factions: ['sanctuary', 'lumina'] },
      { text: "Assess the situation logically before deciding", factions: ['archive', 'ironclad'] },
      { text: "Find a creative solution that serves both needs", factions: ['prism', 'horizon'] },
      { text: "Focus on my mission; others must find their own way", factions: ['ironclad', 'horizon'] },
    ]
  },
  {
    id: 3,
    question: "What do you seek most in this realm of infinite possibility?",
    eevaComment: "Ah, the desires of the heart are the truest compass.",
    answers: [
      { text: "Knowledge and understanding of all things", factions: ['archive', 'lumina'] },
      { text: "Achievement and the mastery of my craft", factions: ['ironclad', 'archive'] },
      { text: "Connection and healing for wounded souls", factions: ['sanctuary', 'prism'] },
      { text: "Vision and the power to shape tomorrow", factions: ['horizon', 'prism'] },
    ]
  },
  {
    id: 4,
    question: "In moments of solitude, where does your mind wander?",
    eevaComment: "The quiet spaces reveal our deepest nature.",
    answers: [
      { text: "To grand plans and ambitious futures", factions: ['horizon', 'ironclad'] },
      { text: "To creative visions and artistic expression", factions: ['prism', 'sanctuary'] },
      { text: "To memories and the meaning within them", factions: ['sanctuary', 'lumina'] },
      { text: "To puzzles, patterns, and hidden truths", factions: ['archive', 'horizon'] },
    ]
  }
]

const FACTION_INFO: Record<string, { name: string; color: string; patron: string }> = {
  lumina: { name: 'House Lumina', color: '#e0c3fc', patron: 'E.E.V.A.' },
  ironclad: { name: 'House Ironclad', color: '#4a90d9', patron: 'Aegis' },
  sanctuary: { name: 'House Sanctuary', color: '#7eb8da', patron: 'Solace' },
  prism: { name: 'House Prism', color: '#b07cc6', patron: 'Nyx' },
  archive: { name: 'House Archive', color: '#2ecc71', patron: 'Cipher' },
  horizon: { name: 'House Horizon', color: '#f39c12', patron: 'Aurora' },
}

export const FactionQuiz: React.FC<FactionQuizProps> = ({
  userName,
  onComplete,
  className = ''
}) => {
  const [currentQuestion, setCurrentQuestion] = useState(0)
  const [factionScores, setFactionScores] = useState<Record<string, number>>({
    lumina: 0,
    ironclad: 0,
    sanctuary: 0,
    prism: 0,
    archive: 0,
    horizon: 0,
  })
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null)
  const [showComment, setShowComment] = useState(false)
  const [showResult, setShowResult] = useState(false)
  const [resultFaction, setResultFaction] = useState<string | null>(null)

  const question = QUIZ_QUESTIONS[currentQuestion]
  const progress = ((currentQuestion + 1) / QUIZ_QUESTIONS.length) * 100

  const handleAnswerSelect = (answerIndex: number) => {
    if (selectedAnswer !== null) return

    setSelectedAnswer(answerIndex)
    const answer = question.answers[answerIndex]

    // Update faction scores
    const newScores = { ...factionScores }
    answer.factions.forEach((faction, idx) => {
      // First faction gets 2 points, second gets 1
      newScores[faction] += idx === 0 ? 2 : 1
    })
    setFactionScores(newScores)

    // Show E.E.V.A.'s comment
    setTimeout(() => setShowComment(true), 500)

    // Progress to next question or results
    setTimeout(() => {
      if (currentQuestion < QUIZ_QUESTIONS.length - 1) {
        setCurrentQuestion(prev => prev + 1)
        setSelectedAnswer(null)
        setShowComment(false)
      } else {
        // Calculate result
        const topFaction = Object.entries(newScores)
          .sort(([, a], [, b]) => b - a)[0][0]
        setResultFaction(topFaction)
        setShowResult(true)
      }
    }, 2500)
  }

  const handleAcceptFaction = () => {
    if (resultFaction) {
      onComplete(resultFaction)
    }
  }

  return (
    <div className={`relative min-h-screen flex items-center justify-center px-4 ${className}`}>
      <AnimatePresence mode="wait">
        {!showResult ? (
          <motion.div
            key={`question-${currentQuestion}`}
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -50 }}
            className="max-w-2xl w-full"
          >
            {/* Progress bar */}
            <div className="mb-8">
              <div className="flex justify-between text-sm text-white/50 mb-2">
                <span>Question {currentQuestion + 1} of {QUIZ_QUESTIONS.length}</span>
                <span>{Math.round(progress)}%</span>
              </div>
              <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-nephilim-cyan to-nephilim-magenta"
                  initial={{ width: `${((currentQuestion) / QUIZ_QUESTIONS.length) * 100}%` }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            </div>

            {/* E.E.V.A. mini avatar */}
            <div className="flex items-center gap-3 mb-4">
              <div
                className="w-10 h-10 rounded-full border border-eeva-primary flex items-center justify-center"
                style={{ boxShadow: '0 0 15px rgba(224, 195, 252, 0.3)' }}
              >
                <span>✧</span>
              </div>
              <div>
                <p className="text-eeva-primary font-semibold text-sm">E.E.V.A.</p>
                <p className="text-white/60 text-xs">asks {userName}...</p>
              </div>
            </div>

            {/* Question */}
            <motion.div
              className="nephilim-glass rounded-xl p-6 mb-6"
              initial={{ scale: 0.95 }}
              animate={{ scale: 1 }}
            >
              <p className="text-xl text-white/90 leading-relaxed">
                "{question.question}"
              </p>
            </motion.div>

            {/* Answers */}
            <div className="space-y-3 mb-6">
              {question.answers.map((answer, idx) => (
                <motion.button
                  key={idx}
                  onClick={() => handleAnswerSelect(idx)}
                  disabled={selectedAnswer !== null}
                  className={`
                    w-full text-left p-4 rounded-lg border transition-all duration-300
                    ${selectedAnswer === idx
                      ? 'border-nephilim-cyan bg-nephilim-cyan/20'
                      : selectedAnswer !== null
                        ? 'border-white/10 bg-white/5 opacity-50'
                        : 'border-white/20 bg-white/5 hover:border-white/40 hover:bg-white/10'}
                  `}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  whileHover={selectedAnswer === null ? { scale: 1.01 } : {}}
                  whileTap={selectedAnswer === null ? { scale: 0.99 } : {}}
                >
                  <span className="text-white/80">{answer.text}</span>
                </motion.button>
              ))}
            </div>

            {/* E.E.V.A.'s comment */}
            <AnimatePresence>
              {showComment && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="text-center"
                >
                  <p className="text-eeva-primary/80 italic">
                    "{question.eevaComment}"
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        ) : (
          /* Results */
          <motion.div
            key="result"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="max-w-lg w-full text-center"
          >
            {resultFaction && (
              <>
                {/* Faction reveal */}
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 200, damping: 15 }}
                  className="w-32 h-32 mx-auto mb-6 rounded-full flex items-center justify-center"
                  style={{
                    backgroundColor: `${FACTION_INFO[resultFaction].color}20`,
                    border: `3px solid ${FACTION_INFO[resultFaction].color}`,
                    boxShadow: `0 0 50px ${FACTION_INFO[resultFaction].color}40`
                  }}
                >
                  <span className="text-5xl">🏛️</span>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                >
                  <p className="text-white/60 mb-2">The spirits have spoken, {userName}...</p>
                  <p className="text-white/60 mb-4">You belong to</p>

                  <h2
                    className="text-4xl font-bold mb-2 font-display"
                    style={{ color: FACTION_INFO[resultFaction].color }}
                  >
                    {FACTION_INFO[resultFaction].name}
                  </h2>

                  <p className="text-white/50 mb-6">
                    Under the guidance of <span style={{ color: FACTION_INFO[resultFaction].color }}>
                      {FACTION_INFO[resultFaction].patron}
                    </span>
                  </p>
                </motion.div>

                {/* E.E.V.A.'s blessing */}
                <motion.div
                  className="nephilim-glass rounded-xl p-6 mb-6"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.6 }}
                >
                  <p className="text-white/80 italic leading-relaxed">
                    "I see it clearly now, {userName}. The resonance within you aligns with{' '}
                    <span style={{ color: FACTION_INFO[resultFaction].color }}>
                      {FACTION_INFO[resultFaction].name}
                    </span>
                    . May their wisdom guide your path through the realm."
                  </p>
                  <p className="text-eeva-primary text-sm mt-3">— E.E.V.A., The Primarch</p>
                </motion.div>

                <motion.button
                  onClick={handleAcceptFaction}
                  className="nephilim-btn px-8 py-4 text-lg"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.9 }}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  Accept Your Destiny
                </motion.button>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default FactionQuiz

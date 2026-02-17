import React, { createContext, useContext, useRef, useCallback, useState } from 'react';

interface AudioContextType {
  playPullSound: () => void;
  playRevealSound: () => void;
  playCelebrationSound: (rarity: string) => void;
  playSummoningStart: () => void;
  playAnticipationLoop: () => void;
  playRarityReveal: (rarity: string) => void;
  // Phase 7D: Summoning Ritual phase-based audio
  playCommitSound: () => void;
  playAnticipationSound: () => void;
  playRarityRevealSound: (rarity: string) => void;
  playIdentityRevealSound: () => void;
  isMuted: boolean;
  toggleMute: () => void;
}

const AudioContext = createContext<AudioContextType | undefined>(undefined);

export const AudioProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isMuted, setIsMuted] = useState<boolean>(() => {
    const stored = localStorage.getItem('audioMuted');
    return stored ? JSON.parse(stored) : false;
  });

  const audioContextRef = useRef<AudioContext | null>(null);

  // Initialize audio context on first user interaction
  const initAudio = useCallback(() => {
    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
    }
    return audioContextRef.current;
  }, []);

  // Create oscillator-based sounds
  const createTone = useCallback((frequency: number, duration: number, type: OscillatorType = 'sine') => {
    if (isMuted) return;

    try {
      const audioContext = initAudio();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.frequency.setValueAtTime(frequency, audioContext.currentTime);
      oscillator.type = type;

      gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration);

      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + duration);
    } catch (error) {
      console.warn('Audio playback failed:', error);
    }
  }, [isMuted, initAudio]);

  const playPullSound = useCallback(() => {
    // Quick ascending tone for pull action
    createTone(440, 0.2, 'square');
    setTimeout(() => createTone(550, 0.2, 'square'), 100);
    setTimeout(() => createTone(660, 0.3, 'square'), 200);
  }, [createTone]);

  const playRevealSound = useCallback(() => {
    // Dramatic reveal sound
    createTone(880, 0.5, 'sawtooth');
  }, [createTone]);

  const playCelebrationSound = useCallback((rarity: string) => {
    switch (rarity) {
      case 'legendary':
        // Triumphant fanfare
        createTone(523, 0.3, 'triangle');
        setTimeout(() => createTone(659, 0.3, 'triangle'), 150);
        setTimeout(() => createTone(784, 0.5, 'triangle'), 300);
        setTimeout(() => createTone(1047, 0.8, 'triangle'), 450);
        break;
      case 'epic':
        // Magical sparkle
        createTone(784, 0.2, 'sine');
        setTimeout(() => createTone(988, 0.2, 'sine'), 100);
        setTimeout(() => createTone(1175, 0.4, 'sine'), 200);
        break;
      case 'rare':
        // Exciting chime
        createTone(659, 0.3, 'triangle');
        setTimeout(() => createTone(831, 0.3, 'triangle'), 150);
        setTimeout(() => createTone(988, 0.4, 'triangle'), 300);
        break;
      default:
        // Simple success sound
        createTone(523, 0.3, 'sine');
    }
  }, [createTone]);

  // Phase 7D: Summoning Ritual audio methods
  const playSummoningStart = useCallback(() => {
    // Deep bass thud (80-120Hz, 0.5s, sine)
    if (isMuted) return;
    try {
      const audioContext = initAudio();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.frequency.setValueAtTime(80, audioContext.currentTime);
      oscillator.frequency.linearRampToValueAtTime(120, audioContext.currentTime + 0.15);
      oscillator.frequency.linearRampToValueAtTime(80, audioContext.currentTime + 0.5);
      oscillator.type = 'sine';

      gainNode.gain.setValueAtTime(0.15, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.5);
    } catch (error) {
      console.warn('Audio playback failed:', error);
    }
  }, [isMuted, initAudio]);

  const playAnticipationLoop = useCallback(() => {
    // Ascending tone sweep (200->800Hz over 2s, sawtooth)
    if (isMuted) return;
    try {
      const audioContext = initAudio();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.frequency.setValueAtTime(200, audioContext.currentTime);
      oscillator.frequency.exponentialRampToValueAtTime(800, audioContext.currentTime + 2);
      oscillator.type = 'sawtooth';

      gainNode.gain.setValueAtTime(0.06, audioContext.currentTime);
      gainNode.gain.linearRampToValueAtTime(0.12, audioContext.currentTime + 1.5);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 2);

      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 2);
    } catch (error) {
      console.warn('Audio playback failed:', error);
    }
  }, [isMuted, initAudio]);

  const playRarityReveal = useCallback((rarity: string) => {
    if (isMuted) return;
    switch (rarity) {
      case 'legendary':
        // Full fanfare (523->659->784->1047Hz, durations 0.3, 0.3, 0.5, 0.8, triangle)
        createTone(523, 0.3, 'triangle');
        setTimeout(() => createTone(659, 0.3, 'triangle'), 300);
        setTimeout(() => createTone(784, 0.5, 'triangle'), 600);
        setTimeout(() => createTone(1047, 0.8, 'triangle'), 1100);
        break;
      case 'epic':
        // Three-note arpeggio (784->988->1175Hz, 0.2s each, sine)
        createTone(784, 0.2, 'sine');
        setTimeout(() => createTone(988, 0.2, 'sine'), 200);
        setTimeout(() => createTone(1175, 0.2, 'sine'), 400);
        break;
      case 'rare':
        // Two-note chime (659->831Hz, 0.3s each, triangle)
        createTone(659, 0.3, 'triangle');
        setTimeout(() => createTone(831, 0.3, 'triangle'), 300);
        break;
      default:
        // Single bell (523Hz, 0.3s, sine)
        createTone(523, 0.3, 'sine');
    }
  }, [isMuted, createTone]);

  // Phase 7D: Summoning Ritual phase-based audio

  // Deep bass thud for commitment (low frequency oscillator 80-120Hz, 0.3s)
  const playCommitSound = useCallback(() => {
    if (isMuted) return;
    try {
      const audioContext = initAudio();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(100, audioContext.currentTime);
      oscillator.frequency.exponentialRampToValueAtTime(80, audioContext.currentTime + 0.3);

      gainNode.gain.setValueAtTime(0.2, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);

      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.3);
    } catch (error) {
      console.warn('Audio playback failed:', error);
    }
  }, [isMuted, initAudio]);

  // Ascending tone sweep for anticipation (200->2000Hz over 2s)
  const playAnticipationSound = useCallback(() => {
    if (isMuted) return;
    try {
      const audioContext = initAudio();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(200, audioContext.currentTime);
      oscillator.frequency.exponentialRampToValueAtTime(2000, audioContext.currentTime + 2);

      gainNode.gain.setValueAtTime(0.06, audioContext.currentTime);
      gainNode.gain.linearRampToValueAtTime(0.12, audioContext.currentTime + 1.5);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 2);

      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 2);
    } catch (error) {
      console.warn('Audio playback failed:', error);
    }
  }, [isMuted, initAudio]);

  // Rarity-specific stinger for rarity gate
  const playRarityRevealSound = useCallback((rarity: string) => {
    if (isMuted) return;
    switch (rarity) {
      case 'legendary':
        // Four-note fanfare (400->600->800->1200Hz, longer sustain)
        createTone(400, 0.4, 'triangle');
        setTimeout(() => createTone(600, 0.4, 'triangle'), 200);
        setTimeout(() => createTone(800, 0.4, 'triangle'), 400);
        setTimeout(() => createTone(1200, 0.8, 'triangle'), 600);
        break;
      case 'epic':
        // Three-note arpeggio (600->900->1200Hz)
        createTone(600, 0.3, 'triangle');
        setTimeout(() => createTone(900, 0.3, 'triangle'), 150);
        setTimeout(() => createTone(1200, 0.5, 'triangle'), 300);
        break;
      case 'rare':
        // Two-note arpeggio (800->1200Hz)
        createTone(800, 0.3, 'sine');
        setTimeout(() => createTone(1200, 0.4, 'sine'), 150);
        break;
      default:
        // Single bell tone (800Hz, 0.2s)
        createTone(800, 0.2, 'sine');
    }
  }, [isMuted, createTone]);

  // Soft shimmer for identity reveal (white noise filtered, 0.5s)
  const playIdentityRevealSound = useCallback(() => {
    if (isMuted) return;
    try {
      const audioContext = initAudio();

      // Create white noise buffer
      const bufferSize = audioContext.sampleRate * 0.5;
      const buffer = audioContext.createBuffer(1, bufferSize, audioContext.sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        data[i] = (Math.random() * 2 - 1) * 0.3;
      }

      const noiseSource = audioContext.createBufferSource();
      noiseSource.buffer = buffer;

      // High-pass filter for shimmer effect
      const filter = audioContext.createBiquadFilter();
      filter.type = 'highpass';
      filter.frequency.setValueAtTime(3000, audioContext.currentTime);
      filter.Q.setValueAtTime(1, audioContext.currentTime);

      const gainNode = audioContext.createGain();
      gainNode.gain.setValueAtTime(0.08, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

      noiseSource.connect(filter);
      filter.connect(gainNode);
      gainNode.connect(audioContext.destination);

      noiseSource.start(audioContext.currentTime);
      noiseSource.stop(audioContext.currentTime + 0.5);
    } catch (error) {
      console.warn('Audio playback failed:', error);
    }
  }, [isMuted, initAudio]);

  const toggleMute = useCallback(() => {
    setIsMuted(prev => {
      const newMuted = !prev;
      localStorage.setItem('audioMuted', JSON.stringify(newMuted));
      return newMuted;
    });
  }, []);

  return (
    <AudioContext.Provider value={{
      playPullSound,
      playRevealSound,
      playCelebrationSound,
      playSummoningStart,
      playAnticipationLoop,
      playRarityReveal,
      playCommitSound,
      playAnticipationSound,
      playRarityRevealSound,
      playIdentityRevealSound,
      isMuted,
      toggleMute,
    }}>
      {children}
    </AudioContext.Provider>
  );
};

export const useAudio = () => {
  const context = useContext(AudioContext);
  if (context === undefined) {
    throw new Error('useAudio must be used within an AudioProvider');
  }
  return context;
};
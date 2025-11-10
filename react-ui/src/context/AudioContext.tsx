import React, { createContext, useContext, useRef, useCallback, useState } from 'react';

interface AudioContextType {
  playPullSound: () => void;
  playRevealSound: () => void;
  playCelebrationSound: (rarity: string) => void;
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
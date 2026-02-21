import React, { createContext, useContext, useRef, useCallback, useState } from 'react';

interface AudioContextType {
  playPullSound: () => void;
  playRevealSound: () => void;
  playCelebrationSound: (order: string) => void;
  playSummoningStart: () => void;
  playAnticipationLoop: () => void;
  playRarityReveal: (order: string) => void;
  playCommitSound: () => void;
  playAnticipationSound: () => void;
  playRarityRevealSound: (order: string) => void;
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

  const playCelebrationSound = useCallback((order: string) => {
    switch (order) {
      case 'archon':
        // Triumphant fanfare
        createTone(523, 0.3, 'triangle');
        setTimeout(() => createTone(659, 0.3, 'triangle'), 150);
        setTimeout(() => createTone(784, 0.5, 'triangle'), 300);
        setTimeout(() => createTone(1047, 0.8, 'triangle'), 450);
        break;
      case 'warden':
        // Magical sparkle
        createTone(784, 0.2, 'sine');
        setTimeout(() => createTone(988, 0.2, 'sine'), 100);
        setTimeout(() => createTone(1175, 0.4, 'sine'), 200);
        break;
      case 'sage':
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

  /** Create an oscillator with gain envelope — reduces boilerplate across audio functions. */
  const createEnvelopedTone = useCallback((
    setup: (ctx: AudioContext, osc: OscillatorNode, gain: GainNode) => void,
    duration: number,
  ) => {
    if (isMuted) return;
    try {
      const ctx = initAudio();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      setup(ctx, osc, gain);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + duration);
    } catch (error) {
      console.warn('Audio playback failed:', error);
    }
  }, [isMuted, initAudio]);

  const playSummoningStart = useCallback(() => {
    // Deep bass thud (80-120Hz, 0.5s, sine)
    createEnvelopedTone((ctx, osc, gain) => {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(80, ctx.currentTime);
      osc.frequency.linearRampToValueAtTime(120, ctx.currentTime + 0.15);
      osc.frequency.linearRampToValueAtTime(80, ctx.currentTime + 0.5);
      gain.gain.setValueAtTime(0.15, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
    }, 0.5);
  }, [createEnvelopedTone]);

  const playAnticipationLoop = useCallback(() => {
    // Ascending tone sweep (200->800Hz over 2s, sawtooth)
    createEnvelopedTone((ctx, osc, gain) => {
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(200, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(800, ctx.currentTime + 2);
      gain.gain.setValueAtTime(0.06, ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0.12, ctx.currentTime + 1.5);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 2);
    }, 2);
  }, [createEnvelopedTone]);

  // Phase 7D: Summoning Ritual phase-based audio

  // Deep bass thud for commitment (100->80Hz, 0.3s)
  const playCommitSound = useCallback(() => {
    createEnvelopedTone((ctx, osc, gain) => {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(100, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(80, ctx.currentTime + 0.3);
      gain.gain.setValueAtTime(0.2, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
    }, 0.3);
  }, [createEnvelopedTone]);

  // Ascending tone sweep for anticipation (200->2000Hz over 2s)
  const playAnticipationSound = useCallback(() => {
    createEnvelopedTone((ctx, osc, gain) => {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(200, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(2000, ctx.currentTime + 2);
      gain.gain.setValueAtTime(0.06, ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0.12, ctx.currentTime + 1.5);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 2);
    }, 2);
  }, [createEnvelopedTone]);

  // Order-specific stinger for rarity gate
  const playRarityRevealSound = useCallback((order: string) => {
    if (isMuted) return;
    switch (order) {
      case 'archon':
        // Four-note fanfare (400->600->800->1200Hz, longer sustain)
        createTone(400, 0.4, 'triangle');
        setTimeout(() => createTone(600, 0.4, 'triangle'), 200);
        setTimeout(() => createTone(800, 0.4, 'triangle'), 400);
        setTimeout(() => createTone(1200, 0.8, 'triangle'), 600);
        break;
      case 'warden':
        // Three-note arpeggio (600->900->1200Hz)
        createTone(600, 0.3, 'triangle');
        setTimeout(() => createTone(900, 0.3, 'triangle'), 150);
        setTimeout(() => createTone(1200, 0.5, 'triangle'), 300);
        break;
      case 'sage':
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
      playRarityReveal: playRarityRevealSound,
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
import React, { useEffect, useState } from 'react';
import { Particles, initParticlesEngine } from '@tsparticles/react';
import { loadSlim } from '@tsparticles/slim';
import type { Engine } from '@tsparticles/engine';

interface EnergyParticlesProps {
  isActive: boolean;
}

const EnergyParticles: React.FC<EnergyParticlesProps> = ({ isActive }) => {
  const [init, setInit] = useState(false);

  useEffect(() => {
    initParticlesEngine(async (engine: Engine) => {
      await loadSlim(engine);
    }).then(() => {
      setInit(true);
    });
  }, []);

  const particlesOptions = {
    background: {
      color: {
        value: 'transparent',
      },
    },
    particles: {
      number: {
        value: 30,
      },
      move: {
        enable: true,
        speed: 1.5,
        direction: 'none' as const,
        random: true,
        straight: false,
        outModes: {
          default: 'out' as const,
        },
      },
      opacity: {
        value: 0.4,
        animation: {
          enable: true,
          speed: 1,
          minimumValue: 0.1,
        },
      },
      size: {
        value: { min: 1, max: 4 },
      },
      color: {
        value: '#ffffff',
      },
    },
  };

  if (!init) {
    return null;
  }

  return (
    <Particles
      id="energy-particles"
      options={particlesOptions}
      className="absolute inset-0 pointer-events-none"
    />
  );
};

export default EnergyParticles;
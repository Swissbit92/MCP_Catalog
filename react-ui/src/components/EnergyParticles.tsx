import React from 'react';
import { Particles } from '@tsparticles/react';

interface EnergyParticlesProps {
  isActive: boolean;
}

const EnergyParticles: React.FC<EnergyParticlesProps> = ({ isActive }) => {

  const particlesOptions = {
    background: {
      color: {
        value: 'transparent',
      },
    },
    particles: {
      number: {
        value: 10,
      },
      move: {
        enable: true,
      },
    },
  };

  return (
    <Particles
      id="energy-particles"
      options={particlesOptions}
      className="absolute inset-0 pointer-events-none"
    />
  );
};

export default EnergyParticles;
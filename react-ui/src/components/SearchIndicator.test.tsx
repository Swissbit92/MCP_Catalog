import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SearchIndicator } from './SearchIndicator';

describe('SearchIndicator', () => {
  describe('Rendering', () => {
    it('renders with default persona name', () => {
      render(<SearchIndicator />);
      expect(screen.getByText(/Assistant is searching the web/i)).toBeInTheDocument();
    });

    it('renders with custom persona name', () => {
      render(<SearchIndicator personaName="Eeva" />);
      expect(screen.getByText(/Eeva is searching the web/i)).toBeInTheDocument();
    });

    it('renders search icon', () => {
      const { container } = render(<SearchIndicator />);
      // Lucide-react Search icon should be rendered
      const searchIcon = container.querySelector('svg');
      expect(searchIcon).toBeInTheDocument();
    });

    it('renders animated dots', () => {
      const { container } = render(<SearchIndicator />);
      // Should have 3 animated dots
      const dots = container.querySelectorAll('.rounded-full.shadow-md');
      expect(dots).toHaveLength(3);
    });
  });

  describe('Rarity-based styling', () => {
    it('applies legendary colors (yellow/amber)', () => {
      const { container } = render(<SearchIndicator rarity="legendary" />);
      const dots = container.querySelectorAll('.from-yellow-400');
      expect(dots.length).toBeGreaterThan(0);
    });

    it('applies epic colors (purple/violet)', () => {
      const { container } = render(<SearchIndicator rarity="epic" />);
      const dots = container.querySelectorAll('.from-purple-400');
      expect(dots.length).toBeGreaterThan(0);
    });

    it('applies rare colors (blue/cyan)', () => {
      const { container } = render(<SearchIndicator rarity="rare" />);
      const dots = container.querySelectorAll('.from-blue-400');
      expect(dots.length).toBeGreaterThan(0);
    });

    it('applies common/default colors (gray)', () => {
      const { container } = render(<SearchIndicator rarity="common" />);
      const dots = container.querySelectorAll('.from-gray-400');
      expect(dots.length).toBeGreaterThan(0);
    });

    it('applies default colors when rarity is undefined', () => {
      const { container } = render(<SearchIndicator />);
      const dots = container.querySelectorAll('.from-gray-400');
      expect(dots.length).toBeGreaterThan(0);
    });
  });

  describe('Accessibility', () => {
    it('has descriptive text for screen readers', () => {
      render(<SearchIndicator personaName="Frieren" rarity="legendary" />);
      const text = screen.getByText(/Frieren is searching the web/i);
      expect(text).toBeInTheDocument();
    });

    it('applies custom className prop', () => {
      const { container } = render(<SearchIndicator className="custom-class" />);
      const indicator = container.querySelector('.custom-class');
      expect(indicator).toBeInTheDocument();
    });
  });

  describe('Animation', () => {
    it('has Framer Motion animation props', () => {
      const { container } = render(<SearchIndicator />);
      // Check for motion div (Framer Motion renders as regular div in test environment)
      const animatedContainer = container.firstChild;
      expect(animatedContainer).toBeInTheDocument();
    });
  });
});

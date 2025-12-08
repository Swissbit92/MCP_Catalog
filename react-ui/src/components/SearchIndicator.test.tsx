import React from 'react';
import { render, screen } from '@testing-library/react';
import { SearchIndicator } from './SearchIndicator';

describe('SearchIndicator', () => {
  it('renders with default props', () => {
    render(<SearchIndicator />);
    expect(screen.getByText(/Assistant is searching the web/i)).toBeInTheDocument();
  });

  it('renders with custom persona name', () => {
    render(<SearchIndicator personaName="Eeva" />);
    expect(screen.getByText(/Eeva is searching the web/i)).toBeInTheDocument();
  });

  it('renders with legendary rarity styling', () => {
    const { container } = render(<SearchIndicator personaName="Frieren" rarity="legendary" />);
    expect(screen.getByText(/Frieren is searching the web/i)).toBeInTheDocument();

    // Check that the component rendered (we can't easily test Tailwind classes)
    const indicator = container.querySelector('[class*="flex items-center"]');
    expect(indicator).toBeInTheDocument();
  });

  it('renders with epic rarity styling', () => {
    render(<SearchIndicator personaName="Gojo" rarity="epic" />);
    expect(screen.getByText(/Gojo is searching the web/i)).toBeInTheDocument();
  });

  it('renders with rare rarity styling', () => {
    render(<SearchIndicator personaName="Itachi" rarity="rare" />);
    expect(screen.getByText(/Itachi is searching the web/i)).toBeInTheDocument();
  });

  it('renders with common rarity styling (default)', () => {
    render(<SearchIndicator personaName="Test" rarity="common" />);
    expect(screen.getByText(/Test is searching the web/i)).toBeInTheDocument();
  });

  it('renders search icon', () => {
    const { container } = render(<SearchIndicator />);
    // Lucide icon renders as svg
    const icon = container.querySelector('svg');
    expect(icon).toBeInTheDocument();
  });

  it('renders animated dots', () => {
    const { container } = render(<SearchIndicator />);
    // Should have 3 animated dots
    const dots = container.querySelectorAll('[class*="rounded-full"]');
    expect(dots.length).toBeGreaterThanOrEqual(3);
  });

  it('applies custom className', () => {
    const { container } = render(<SearchIndicator className="custom-class" />);
    const indicator = container.firstChild;
    expect(indicator).toHaveClass('custom-class');
  });
});

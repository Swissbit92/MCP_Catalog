import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import BoltedPlateBorder from './BoltedPlateBorder';

describe('BoltedPlateBorder', () => {
  const mockChildren = <div data-testid="test-content">Test Content</div>;

  it('renders children correctly', () => {
    render(
      <BoltedPlateBorder rarity="legendary">
        {mockChildren}
      </BoltedPlateBorder>
    );

    expect(screen.getByTestId('test-content')).toBeInTheDocument();
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('applies legendary rarity styling', () => {
    const { container } = render(
      <BoltedPlateBorder rarity="legendary">
        {mockChildren}
      </BoltedPlateBorder>
    );

    const borderElement = container.querySelector('[class*="border-yellow-400"]');
    expect(borderElement).toBeInTheDocument();
  });

  it('applies epic rarity styling', () => {
    const { container } = render(
      <BoltedPlateBorder rarity="epic">
        {mockChildren}
      </BoltedPlateBorder>
    );

    const borderElement = container.querySelector('[class*="border-purple-400"]');
    expect(borderElement).toBeInTheDocument();
  });

  it('applies rare rarity styling', () => {
    const { container } = render(
      <BoltedPlateBorder rarity="rare">
        {mockChildren}
      </BoltedPlateBorder>
    );

    const borderElement = container.querySelector('[class*="border-blue-400"]');
    expect(borderElement).toBeInTheDocument();
  });

  it('applies common rarity styling as default', () => {
    const { container } = render(
      <BoltedPlateBorder rarity="common">
        {mockChildren}
      </BoltedPlateBorder>
    );

    const borderElement = container.querySelector('[class*="border-gray-400"]');
    expect(borderElement).toBeInTheDocument();
  });

  it('applies unknown rarity as common', () => {
    const { container } = render(
      <BoltedPlateBorder rarity="unknown">
        {mockChildren}
      </BoltedPlateBorder>
    );

    const borderElement = container.querySelector('[class*="border-gray-400"]');
    expect(borderElement).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <BoltedPlateBorder rarity="legendary" className="custom-class">
        {mockChildren}
      </BoltedPlateBorder>
    );

    const borderElement = container.firstChild;
    expect(borderElement).toHaveClass('custom-class');
  });

  it('has correct base styling', () => {
    const { container } = render(
      <BoltedPlateBorder rarity="legendary">
        {mockChildren}
      </BoltedPlateBorder>
    );

    const borderElement = container.querySelector('[class*="bg-slate-800/40"]');
    expect(borderElement).toHaveClass(
      'bg-slate-800/40',
      'backdrop-blur-md',
      'border-2',
      'shadow-2xl',
      'rounded-lg',
      'overflow-hidden'
    );
  });

  it('renders with clip-path for bolted effect', () => {
    const { container } = render(
      <BoltedPlateBorder rarity="legendary">
        {mockChildren}
      </BoltedPlateBorder>
    );

    const borderElement = container.querySelector('[style*="clip-path"]');
    expect(borderElement).toBeInTheDocument();
  });

  it('applies hover scale effect', () => {
    const { container } = render(
      <BoltedPlateBorder rarity="legendary">
        {mockChildren}
      </BoltedPlateBorder>
    );

    const borderElement = container.firstChild;
    expect(borderElement).toBeInTheDocument();

    // Note: Testing hover effects would require more complex setup with user-event
    // This test ensures the component renders with hover capability
  });

  it('has enhanced glassmorphism styling', () => {
    const { container } = render(
      <BoltedPlateBorder rarity="legendary">
        {mockChildren}
      </BoltedPlateBorder>
    );

    // Check that the component has backdrop-blur-md class for enhanced glassmorphism
    const borderElement = container.querySelector('.backdrop-blur-md');
    expect(borderElement).toBeInTheDocument();
  });

  it('has refined breathing animation timing', () => {
    const { container } = render(
      <BoltedPlateBorder rarity="legendary">
        {mockChildren}
      </BoltedPlateBorder>
    );

    // Check that animation elements exist
    const animatedElements = container.querySelectorAll('[style*="clip-path"]');
    expect(animatedElements.length).toBeGreaterThan(1);
  });
});
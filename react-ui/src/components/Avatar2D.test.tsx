import React from 'react';
import { render, screen } from '@testing-library/react';
import { Avatar2D } from './Avatar2D';

describe('Avatar2D', () => {
  it('renders with image when src is provided', () => {
    render(<Avatar2D src="/test-avatar.png" alt="Test User" />);

    const img = screen.getByAltText('Test User');
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute('src', '/test-avatar.png');
  });

  it('renders fallback initial when no src is provided', () => {
    render(<Avatar2D alt="John Doe" />);

    expect(screen.getByText('J')).toBeInTheDocument();
  });

  it('renders custom fallback when provided', () => {
    render(<Avatar2D alt="Test User" fallback="?" />);

    expect(screen.getByText('?')).toBeInTheDocument();
  });

  it('applies correct size classes', () => {
    const { container: xsContainer } = render(<Avatar2D alt="Test" size="xs" />);
    const { container: smContainer } = render(<Avatar2D alt="Test" size="sm" />);
    const { container: mdContainer } = render(<Avatar2D alt="Test" size="md" />);
    const { container: lgContainer } = render(<Avatar2D alt="Test" size="lg" />);

    expect(xsContainer.firstChild).toHaveClass('w-6', 'h-6');
    expect(smContainer.firstChild).toHaveClass('w-8', 'h-8');
    expect(mdContainer.firstChild).toHaveClass('w-10', 'h-10');
    expect(lgContainer.firstChild).toHaveClass('w-12', 'h-12');
  });

  it('applies custom className', () => {
    const { container } = render(<Avatar2D alt="Test" className="custom-avatar" />);

    expect(container.firstChild).toHaveClass('custom-avatar');
  });

  it('handles image load error gracefully', () => {
    render(<Avatar2D src="/broken-image.png" alt="Test User" />);

    const img = screen.getByAltText('Test User');
    expect(img).toBeInTheDocument();

    // Simulate error
    img.dispatchEvent(new Event('error'));

    // Should still render (error handling is in the component)
    expect(img).toBeInTheDocument();
  });

  it('applies legendary rarity styles', () => {
    const { container } = render(<Avatar2D alt="Test" rarity="legendary" />);

    expect(container.firstChild).toHaveClass('ring-2', 'ring-yellow-400', 'shadow-lg', 'shadow-yellow-500/30');
  });

  it('applies epic rarity styles', () => {
    const { container } = render(<Avatar2D alt="Test" rarity="epic" />);

    expect(container.firstChild).toHaveClass('ring-2', 'ring-purple-400', 'shadow-lg', 'shadow-purple-500/30');
  });

  it('applies rare rarity styles', () => {
    const { container } = render(<Avatar2D alt="Test" rarity="rare" />);

    expect(container.firstChild).toHaveClass('ring-2', 'ring-blue-400', 'shadow-lg', 'shadow-blue-500/30');
  });

  it('applies common rarity styles by default', () => {
    const { container } = render(<Avatar2D alt="Test" rarity="common" />);

    expect(container.firstChild).toHaveClass('ring-1', 'ring-gray-400', 'shadow-md', 'shadow-gray-400/20');
  });

  it('applies hover scale effect', () => {
    const { container } = render(<Avatar2D alt="Test" />);

    expect(container.firstChild).toHaveClass('hover:scale-105');
  });
});
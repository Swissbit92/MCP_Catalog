import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './App';
import { PersonaProvider } from '../src/context/PersonaContext';

test('renders App component with header links', () => {
  render(
    <MemoryRouter>
      <PersonaProvider>
        <App />
      </PersonaProvider>
    </MemoryRouter>
  );
  const characterSelectionLink = screen.getByRole('link', { name: /Character Selection/i });
  const chatLink = screen.getByRole('link', { name: /Chat/i });

  expect(characterSelectionLink).toBeInTheDocument();
  expect(chatLink).toBeInTheDocument();
});
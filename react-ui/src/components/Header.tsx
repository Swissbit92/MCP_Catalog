import React from 'react';
import { Link } from 'react-router-dom';

const Header: React.FC = () => {
  return (
    <header style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '1rem',
      backgroundColor: '#f8f8f8',
      borderBottom: '1px solid #e7e7e7',
    }}>
      <nav>
        <Link to="/" style={{ marginRight: '1rem', textDecoration: 'none', color: '#007bff' }}>
          Home
        </Link>
        <Link to="/select" style={{ marginRight: '1rem', textDecoration: 'none', color: '#007bff' }}>
          Characters
        </Link>
        <Link to="/chat" style={{ textDecoration: 'none', color: '#007bff' }}>
          Chat
        </Link>
      </nav>
    </header>
  );
};

export default Header;

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { RichContent } from './RichContent';

describe('RichContent', () => {
  it('renders plain text content correctly', () => {
    const content = 'This is a simple text message.';
    render(<RichContent content={content} />);

    expect(screen.getByText(content)).toBeInTheDocument();
  });

  it('renders JSON content with formatting', () => {
    const jsonContent = '{"name": "John", "age": 30, "city": "New York"}';
    render(<RichContent content={jsonContent} />);

    expect(screen.getByText('JSON Response')).toBeInTheDocument();
    // The formatted JSON should contain the expected content
    const preElement = screen.getByText((content) => content.includes('"name": "John"'));
    expect(preElement).toBeInTheDocument();
  });

  it('renders collapsible JSON for long content', () => {
    // Create a long JSON string
    const longJson = JSON.stringify({
      users: Array.from({ length: 20 }, (_, i) => ({
        id: i,
        name: `User ${i}`,
        email: `user${i}@example.com`,
        details: {
          age: 20 + i,
          city: `City ${i}`,
          hobbies: ['reading', 'coding', 'gaming']
        }
      }))
    });

    render(<RichContent content={longJson} />);

    expect(screen.getByText('JSON Response')).toBeInTheDocument();
    expect(screen.getByText('Show more')).toBeInTheDocument();
  });

  it('expands and collapses long JSON content', () => {
    const longJson = JSON.stringify({
      users: Array.from({ length: 20 }, (_, i) => ({
        id: i,
        name: `User ${i}`,
        email: `user${i}@example.com`
      }))
    });

    render(<RichContent content={longJson} />);

    const showMoreButton = screen.getByText('Show more');
    fireEvent.click(showMoreButton);

    expect(screen.getByText('Show less')).toBeInTheDocument();
    expect(screen.queryByText('Show more')).not.toBeInTheDocument();

    const showLessButton = screen.getByText('Show less');
    fireEvent.click(showLessButton);

    expect(screen.getByText('Show more')).toBeInTheDocument();
    expect(screen.queryByText('Show less')).not.toBeInTheDocument();
  });

  it('renders code blocks with syntax highlighting', () => {
    const codeBlock = '```javascript\nconsole.log("Hello, World!");\n```';
    render(<RichContent content={codeBlock} />);

    expect(screen.getByText('Code (javascript)')).toBeInTheDocument();
    // The syntax highlighter should render the code
    expect(screen.getByText('console.log("Hello, World!");')).toBeInTheDocument();
  });

  it('renders code blocks with default language when none specified', () => {
    const codeBlock = '```\nplain text code\n```';
    render(<RichContent content={codeBlock} />);

    expect(screen.getByText('Code (text)')).toBeInTheDocument();
  });

  it('handles invalid JSON gracefully', () => {
    const invalidJson = '{"name": "John", "age": 30,}'; // trailing comma
    render(<RichContent content={invalidJson} />);

    // Should render as plain text since it's not valid JSON
    expect(screen.getByText(invalidJson)).toBeInTheDocument();
    expect(screen.queryByText('JSON Response')).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    const content = 'Test content';
    const customClass = 'custom-class';
    const { container } = render(<RichContent content={content} className={customClass} />);

    // The custom class should be applied to the root element
    expect(container.firstChild).toHaveClass(customClass);
  });
});
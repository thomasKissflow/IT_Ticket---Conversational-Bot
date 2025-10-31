import React from 'react';
import type { Message } from '../types/conversation';
import './ConversationDisplay.css';

interface ConversationDisplayProps {
  messages: Message[];
}

const ConversationDisplay: React.FC<ConversationDisplayProps> = ({ messages }) => {
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const formatTime = (timestamp: Date) => {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="conversation-display">
      <div className="messages-container">
        {messages.map((message) => (
          <div key={message.id} className={`message ${message.type}`}>
            <div className="message-header">
              <span className="message-type">
                {message.type === 'user' ? 'You' : 
                 message.type === 'assistant' ? 'Assistant' : 'System'}
              </span>
              <span className="message-time">{formatTime(message.timestamp)}</span>
              {message.confidence && (
                <span className="confidence-score">
                  Confidence: {(message.confidence * 100).toFixed(0)}%
                </span>
              )}
            </div>
            <div className="message-content">{message.content}</div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};

export default ConversationDisplay;
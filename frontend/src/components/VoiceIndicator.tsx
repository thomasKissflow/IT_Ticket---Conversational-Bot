import React from 'react';
import type { VoiceIndicatorProps } from '../types/conversation';
import './VoiceIndicator.css';

const VoiceIndicator: React.FC<VoiceIndicatorProps> = ({ 
  isListening, 
  isProcessing, 
  isPlaying 
}) => {
  const getStatusText = () => {
    if (isPlaying) return 'Speaking...';
    if (isProcessing) return 'Processing...';
    if (isListening) return 'Listening...';
    return 'Ready';
  };

  const getStatusIcon = () => {
    if (isPlaying) return '';
    if (isProcessing) return '';
    if (isListening) return '';
    return '';
  };

  const getStatusClass = () => {
    if (isPlaying) return 'playing';
    if (isProcessing) return 'processing';
    if (isListening) return 'listening';
    return 'ready';
  };

  return (
    <div className={`voice-indicator ${getStatusClass()}`}>
      <div className="status-icon">
        {getStatusIcon()}
      </div>
      <div className="status-text">
        {getStatusText()}
      </div>
      <div className="status-animation">
        {isListening && (
          <div className="listening-waves">
            <div className="wave"></div>
            <div className="wave"></div>
            <div className="wave"></div>
          </div>
        )}
        {isProcessing && (
          <div className="processing-spinner">
            <div className="spinner"></div>
          </div>
        )}
        {isPlaying && (
          <div className="playing-bars">
            <div className="bar"></div>
            <div className="bar"></div>
            <div className="bar"></div>
            <div className="bar"></div>
          </div>
        )}
      </div>
    </div>
  );
};

export default VoiceIndicator;
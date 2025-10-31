import React from 'react';
import './TranscriptionDisplay.css';

interface TranscriptionDisplayProps {
  currentTranscript: string;
  isListening: boolean;
}

const TranscriptionDisplay: React.FC<TranscriptionDisplayProps> = ({ 
  currentTranscript, 
  isListening 
}) => {
  return (
    <div className={`transcription-display ${isListening ? 'active' : ''}`}>
      <div className="transcription-header">
        <span className="transcription-label">
          {isListening ? 'Live Transcription' : '📝 Last Transcription'}
        </span>
      </div>
      <div className="transcription-content">
        {currentTranscript || (isListening ? 'Speak now...' : 'No transcription yet')}
        {isListening && <span className="cursor-blink">|</span>}
      </div>
    </div>
  );
};

export default TranscriptionDisplay;
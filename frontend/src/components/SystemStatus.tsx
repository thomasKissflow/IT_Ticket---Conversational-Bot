import React from 'react';
import './SystemStatus.css';

interface SystemStatusProps {
  agentStatus: string;
  escalationAlert?: {
    message: string;
    timestamp: Date;
  };
  connectionStatus: 'connected' | 'connecting' | 'disconnected';
}

const SystemStatus: React.FC<SystemStatusProps> = ({ 
  agentStatus, 
  escalationAlert, 
  connectionStatus 
}) => {
  const getConnectionIcon = () => {
    switch (connectionStatus) {
      case 'connected': return '🟢';
      case 'connecting': return '🟡';
      case 'disconnected': return '🔴';
      default: return '⚪';
    }
  };

  const getConnectionText = () => {
    switch (connectionStatus) {
      case 'connected': return 'Connected';
      case 'connecting': return 'Connecting...';
      case 'disconnected': return 'Disconnected';
      default: return 'Unknown';
    }
  };

  return (
    <div className="system-status">
      <div className="status-row">
        <div className="status-item">
          <span className="status-label">Connection:</span>
          <span className={`status-value connection-${connectionStatus}`}>
            {getConnectionIcon()} {getConnectionText()}
          </span>
        </div>
        <div className="status-item">
          <span className="status-label">Agent:</span>
          <span className="status-value">{agentStatus || 'Ready'}</span>
        </div>
      </div>
      
      {escalationAlert && (
        <div className="escalation-alert">
          <div className="alert-header">
            <span className="alert-icon">⚠️</span>
            <span className="alert-title">Escalation Required</span>
            <span className="alert-time">
              {escalationAlert.timestamp.toLocaleTimeString()}
            </span>
          </div>
          <div className="alert-message">
            {escalationAlert.message}
          </div>
        </div>
      )}
    </div>
  );
};

export default SystemStatus;
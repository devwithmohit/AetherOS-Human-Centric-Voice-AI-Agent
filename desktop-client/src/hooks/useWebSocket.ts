import { useEffect, useState } from 'react';
import { wsService } from '@services/websocket';

export const useWebSocket = (url: string) => {
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Connect to WebSocket
    wsService.connect(url).catch((error) => {
      console.error('Failed to connect to WebSocket:', error);
    });

    // Set up connection state polling
    const interval = setInterval(() => {
      setIsConnected(wsService.isConnected());
    }, 1000);

    return () => {
      clearInterval(interval);
      // Don't disconnect on unmount - keep connection alive
    };
  }, [url]);

  const sendMessage = (message: any) => {
    wsService.send(message);
  };

  return {
    isConnected,
    sendMessage,
  };
};

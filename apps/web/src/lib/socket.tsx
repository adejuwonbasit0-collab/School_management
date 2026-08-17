'use client';

import { createContext, useContext, useEffect, useRef, type ReactNode } from 'react';
import { io, Socket } from 'socket.io-client';
import { useAuthStore } from '@/store/auth.store';
import toast from 'react-hot-toast';

const SocketContext = createContext<Socket | null>(null);

export function SocketProvider({ children }: { children: ReactNode }) {
  const socketRef = useRef<Socket | null>(null);
  const { accessToken, isAuthenticated, user } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated || !accessToken) return;

    const socket = io(process.env.NEXT_PUBLIC_SOCKET_URL || 'http://localhost:3001', {
      auth: { token: accessToken },
      transports: ['websocket', 'polling'],
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    socket.on('connect', () => {
      if (user?.schoolId) socket.emit('join-school', user.schoolId);
    });

    socket.on('notification', (data: any) => {
      toast(data.title || data.message, {
        icon: data.type === 'error' ? '❌' : data.type === 'warning' ? '⚠️' : '🔔',
      });
    });

    socket.on('attendance-marked', () => {
      // Invalidate attendance queries
      window.dispatchEvent(new CustomEvent('refetch-attendance'));
    });

    socket.on('payment-received', (data: any) => {
      toast.success(`Payment received: ₦${data.amount?.toLocaleString()}`);
      window.dispatchEvent(new CustomEvent('refetch-finance'));
    });

    socketRef.current = socket;

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [isAuthenticated, accessToken]);

  return (
    <SocketContext.Provider value={socketRef.current}>
      {children}
    </SocketContext.Provider>
  );
}

export const useSocket = () => useContext(SocketContext);

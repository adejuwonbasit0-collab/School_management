import { WebSocketGateway, WebSocketServer, SubscribeMessage, OnGatewayConnection, OnGatewayDisconnect } from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';
import { Injectable, Logger } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';

@WebSocketGateway({ cors: true, namespace: '/' })
@Injectable()
export class RealtimeGateway implements OnGatewayConnection, OnGatewayDisconnect {
  @WebSocketServer() server: Server;
  private logger = new Logger(RealtimeGateway.name);
  private clients = new Map<string, string>();

  constructor(private jwtService: JwtService) {}

  async handleConnection(client: Socket) {
    try {
      const token = client.handshake.auth.token || client.handshake.headers.authorization?.split(' ')[1];
      if (!token) {
        this.logger.warn('Client connected without token, disconnecting');
        client.disconnect();
        return;
      }
      const payload = this.jwtService.verify(token);
      client.data.userId = payload.sub;
      this.clients.set(client.id, payload.sub);
      this.logger.log(`Client ${client.id} connected as user ${payload.sub}`);
    } catch (err) {
      this.logger.warn('Invalid token, disconnecting');
      client.disconnect();
    }
  }

  handleDisconnect(client: Socket) {
    this.clients.delete(client.id);
    this.logger.log(`Client ${client.id} disconnected`);
  }

  @SubscribeMessage('chat:send')
  async handleChat(client: Socket, payload: { roomId: string; content: string }) {
    client.to(payload.roomId).emit('chat:message', {
      userId: client.data.userId,
      content: payload.content,
      timestamp: new Date().toISOString(),
    });
  }

  @SubscribeMessage('join:room')
  handleJoinRoom(client: Socket, payload: { roomId: string }) {
    client.join(payload.roomId);
    this.logger.log(`Client ${client.id} joined room ${payload.roomId}`);
  }

  @SubscribeMessage('leave:room')
  handleLeaveRoom(client: Socket, payload: { roomId: string }) {
    client.leave(payload.roomId);
    this.logger.log(`Client ${client.id} left room ${payload.roomId}`);
  }
}

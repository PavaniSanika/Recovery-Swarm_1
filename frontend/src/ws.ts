import { WsMessage } from "./types";

export interface WebSocketClientOptions {
  patientId: string;
  onMessage: (msg: WsMessage) => void;
  onError?: (err: Event) => void;
  onClose?: (event: CloseEvent) => void;
  onOpen?: () => void;
}

export class RecoverySwarmWebSocket {
  private socket: WebSocket | null = null;
  private readonly url: string;
  private readonly options: WebSocketClientOptions;

  constructor(options: WebSocketClientOptions) {
    this.options = options;
    let baseApi = "http://localhost:8000";
    try {
      if (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.VITE_API_BASE_URL) {
        baseApi = import.meta.env.VITE_API_BASE_URL as string;
      }
    } catch {
      // Ignore
    }
    const wsBase = baseApi.replace(/^http/, "ws").replace(/\/+$/, "");
    this.url = `${wsBase}/ws/patients/${encodeURIComponent(options.patientId)}`;
  }

  public connect(): void {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.socket = new WebSocket(this.url);

    this.socket.onopen = () => {
      if (this.options.onOpen) {
        this.options.onOpen();
      }
    };

    this.socket.onmessage = (event: MessageEvent<string>) => {
      try {
        const raw = JSON.parse(event.data) as WsMessage;
        this.handleMessage(raw);
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err, event.data);
      }
    };

    this.socket.onerror = (event: Event) => {
      if (this.options.onError) {
        this.options.onError(event);
      }
    };

    this.socket.onclose = (event: CloseEvent) => {
      if (this.options.onClose) {
        this.options.onClose(event);
      }
    };
  }

  public disconnect(): void {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  private handleMessage(msg: WsMessage): void {
    switch (msg.type) {
      case "twin_update":
      case "debate_message":
      case "agent_status":
      case "plan":
      case "safety":
      case "escalation":
        this.options.onMessage(msg);
        break;
    }
  }
}

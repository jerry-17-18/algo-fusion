import { useRef, useState } from "react";

import type { ClinicalSocketUpdate } from "../lib/types";

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000/api/v1";

type SocketEvent =
  | ClinicalSocketUpdate
  | { type: "connected"; session_id: string }
  | { type: "noise"; message: string; language: string }
  | { type: "warning"; message: string }
  | { type: "error"; message: string }
  | { type: "stopped"; session_id: string };

export function useClinicalSocket(onMessage: (event: SocketEvent) => void) {
  const socketRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  async function connect(token: string, sessionId: string): Promise<void> {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    await new Promise<void>((resolve, reject) => {
      const url = `${WS_BASE_URL}/ws/clinical?token=${encodeURIComponent(token)}&session_id=${sessionId}`;
      const socket = new WebSocket(url);
      socketRef.current = socket;

      socket.onopen = () => {
        setIsConnected(true);
        resolve();
      };
      socket.onerror = () => {
        setIsConnected(false);
        reject(new Error("WebSocket connection failed"));
      };
      socket.onclose = () => {
        setIsConnected(false);
      };
      socket.onmessage = (event) => {
        onMessage(JSON.parse(event.data) as SocketEvent);
      };
    });
  }

  function disconnect() {
    socketRef.current?.close();
    socketRef.current = null;
    setIsConnected(false);
  }

  async function sendAudioChunk(blob: Blob, sessionId: string) {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    const base64 = await blobToBase64(blob);
    socketRef.current.send(
      JSON.stringify({
        type: "audio_chunk",
        session_id: sessionId,
        mime_type: blob.type || "audio/webm",
        data: base64,
      }),
    );
  }

  function stop(sessionId: string) {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      return;
    }
    socketRef.current.send(JSON.stringify({ type: "stop", session_id: sessionId }));
  }

  return { connect, disconnect, isConnected, sendAudioChunk, stop };
}

async function blobToBase64(blob: Blob): Promise<string> {
  const buffer = await blob.arrayBuffer();
  let binary = "";
  const bytes = new Uint8Array(buffer);
  const chunkSize = 0x8000;

  for (let index = 0; index < bytes.length; index += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(index, index + chunkSize));
  }

  return btoa(binary);
}


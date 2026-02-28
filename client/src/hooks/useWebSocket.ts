"use client";

import { useEffect, useRef, useState, useCallback } from "react";

export function useWebSocket(
  tripId: string | null,
  onEvent: (event: Record<string, unknown>) => void
) {
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    if (!tripId) return;

    const es = new EventSource(`/api/trips/${tripId}/events`);
    esRef.current = es;

    es.onopen = () => {
      setConnected(true);
    };

    es.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data);
        if (data.type === "heartbeat") return;
        onEventRef.current(data);
      } catch {
        // Ignore malformed messages
      }
    };

    es.onerror = () => {
      setConnected(false);
      es.close();
      esRef.current = null;
    };
  }, [tripId]);

  useEffect(() => {
    connect();
    return () => {
      esRef.current?.close();
      esRef.current = null;
    };
  }, [connect]);

  return { connected };
}

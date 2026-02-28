"use client";

import { useEffect, useRef, useState, useCallback } from "react";

const MAX_RETRIES = 5;
const BASE_DELAY_MS = 1000;

export function useWebSocket(
  tripId: string | null,
  onEvent: (event: Record<string, unknown>) => void
) {
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);
  const onEventRef = useRef(onEvent);
  const retriesRef = useRef(0);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    if (!tripId) return;

    esRef.current?.close();

    const es = new EventSource(`/api/trips/${tripId}/events`);
    esRef.current = es;

    es.onopen = () => {
      setConnected(true);
      retriesRef.current = 0;
    };

    es.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data);
        if (data.type === "heartbeat") return;
        onEventRef.current(data);

        if (data.type === "trip_completed" || data.type === "trip_failed") {
          es.close();
          esRef.current = null;
          setConnected(false);
        }
      } catch (err) {
        console.warn("Malformed SSE message:", err);
      }
    };

    es.onerror = () => {
      setConnected(false);
      es.close();
      esRef.current = null;

      if (retriesRef.current < MAX_RETRIES) {
        const delay = BASE_DELAY_MS * Math.pow(2, retriesRef.current);
        retriesRef.current += 1;
        retryTimerRef.current = setTimeout(() => {
          connect();
        }, delay);
      }
    };
  }, [tripId]);

  useEffect(() => {
    retriesRef.current = 0;
    connect();
    return () => {
      esRef.current?.close();
      esRef.current = null;
      if (retryTimerRef.current) {
        clearTimeout(retryTimerRef.current);
        retryTimerRef.current = null;
      }
    };
  }, [connect]);

  return { connected };
}

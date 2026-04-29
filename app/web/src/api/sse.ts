import { useEffect, useRef } from "react";

type Handler = (event: string, data: unknown) => void;

export function useSSE(url: string, onMessage: Handler, deps: unknown[] = []): void {
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    let es: EventSource | null = null;
    let cancelled = false;
    let attempt = 0;

    const connect = () => {
      if (cancelled) return;
      es = new EventSource(url);

      es.addEventListener("open", () => {
        attempt = 0;
      });

      const dispatch = (eventName: string) => (ev: MessageEvent<string>) => {
        try {
          const data = JSON.parse(ev.data);
          onMessageRef.current(eventName, data);
        } catch {
          /* ignore malformed payload */
        }
      };

      ["snapshot", "kpis", "positions", "position", "event"].forEach((name) => {
        es!.addEventListener(name, dispatch(name) as EventListener);
      });

      es.onerror = () => {
        if (cancelled) return;
        es?.close();
        es = null;
        attempt += 1;
        const backoff = Math.min(1000 * 2 ** Math.min(attempt, 5), 15000);
        setTimeout(connect, backoff);
      };
    };

    connect();
    return () => {
      cancelled = true;
      es?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, ...deps]);
}

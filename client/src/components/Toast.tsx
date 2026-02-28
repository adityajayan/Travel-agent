"use client";

import { createContext, useCallback, useContext, useState } from "react";

interface ToastMessage {
  id: number;
  text: string;
  variant: "error" | "success" | "info";
}

interface ToastContextValue {
  toast: (text: string, variant?: ToastMessage["variant"]) => void;
}

const ToastContext = createContext<ToastContextValue>({
  toast: () => {},
});

export function useToast() {
  return useContext(ToastContext);
}

let nextId = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [messages, setMessages] = useState<ToastMessage[]>([]);

  const toast = useCallback((text: string, variant: ToastMessage["variant"] = "error") => {
    const id = nextId++;
    setMessages((prev) => [...prev, { id, text, variant }]);
    setTimeout(() => {
      setMessages((prev) => prev.filter((m) => m.id !== id));
    }, 5000);
  }, []);

  const dismiss = (id: number) => {
    setMessages((prev) => prev.filter((m) => m.id !== id));
  };

  const variantStyles: Record<string, string> = {
    error: "bg-red-600",
    success: "bg-green-600",
    info: "bg-blue-600",
  };

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`${variantStyles[msg.variant]} text-white text-sm px-4 py-3 rounded-lg shadow-lg flex items-center justify-between gap-3 animate-slide-up`}
          >
            <span>{msg.text}</span>
            <button
              onClick={() => dismiss(msg.id)}
              className="text-white/70 hover:text-white flex-shrink-0"
            >
              &times;
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

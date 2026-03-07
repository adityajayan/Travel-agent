"use client";

import { useState, useEffect, useRef } from "react";
import type { ChatMessage } from "@/lib/itinerary-types";
import { apiClient } from "@/lib/api";

interface TripChatProps {
  tripId: string;
}

const quickActions = [
  "Swap hotel",
  "Find cheaper flights",
  "Add restaurants",
  "Export calendar",
];

export default function TripChat({ tripId }: TripChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch chat history on mount
  useEffect(() => {
    apiClient.getChatHistory(tripId).then(setMessages).catch(() => {});
  }, [tripId]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;

    setInput("");
    setSending(true);

    // Optimistic user message
    const tempUserMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      trip_id: tripId,
      role: "user",
      content: text,
      metadata_json: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const response = await apiClient.sendChatMessage(tripId, text);
      // Replace temp message and add response
      setMessages((prev) => {
        const filtered = prev.filter((m) => m.id !== tempUserMsg.id);
        return [
          ...filtered,
          { ...tempUserMsg, id: `user-${Date.now()}` },
          response,
        ];
      });
    } catch {
      // Keep the user message, add error response
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          trip_id: tripId,
          role: "assistant",
          content: "Sorry, I couldn't process that request. Please try again.",
          metadata_json: null,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-2 border-border-heavy bg-white shadow-hard-sm flex flex-col">
      {/* Chat header — inverted */}
      <button
        className="bg-contrast px-4 py-2.5 flex items-center justify-between w-full"
        onClick={() => setCollapsed(!collapsed)}
      >
        <div className="flex items-center gap-2">
          <span className="w-6 h-6 bg-paper flex items-center justify-center flex-shrink-0">
            <span className="font-display text-contrast text-xs font-medium">C</span>
          </span>
          <span className="font-ui text-[0.72rem] font-bold uppercase tracking-[0.14em] text-paper">
            Chat with Concierge
          </span>
        </div>
        <svg
          className={`h-4 w-4 text-paper/50 transition-transform ${collapsed ? "" : "rotate-180"}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {!collapsed && (
        <>
          {/* Messages area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 max-h-80 min-h-[200px] bg-paper">
            {messages.length === 0 && (
              <div className="text-center py-6">
                <p className="font-body text-sm text-text-ghost">
                  Ask Concierge about your trip
                </p>
              </div>
            )}
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} stagger-fade-up`}
              >
                <div
                  className={`max-w-[85%] px-3 py-2 ${
                    msg.role === "user"
                      ? "bg-contrast text-paper"
                      : "bg-white border-[1.5px] border-border-light"
                  }`}
                >
                  <p className={`font-body text-sm font-light ${msg.role === "user" ? "" : "text-text-mid"}`}>
                    {msg.content}
                  </p>
                </div>
              </div>
            ))}
            {sending && (
              <div className="flex justify-start">
                <div className="bg-white border-[1.5px] border-border-light px-3 py-2">
                  <div className="flex gap-1.5">
                    <span className="h-2 w-2 bg-border-heavy animate-pulse-dot" />
                    <span className="h-2 w-2 bg-border-heavy animate-pulse-dot" style={{ animationDelay: "0.3s" }} />
                    <span className="h-2 w-2 bg-border-heavy animate-pulse-dot" style={{ animationDelay: "0.6s" }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick actions */}
          <div className="px-4 py-2 flex gap-2 flex-wrap border-t border-border-light">
            {quickActions.map((action) => (
              <button
                key={action}
                onClick={() => setInput(action)}
                className="px-2.5 py-1 border-[1.5px] border-accent-border font-ui text-[0.6rem] font-bold uppercase tracking-[0.1em] text-accent hover:bg-accent-soft btn-transition"
              >
                {action}
              </button>
            ))}
          </div>

          {/* Input area */}
          <div className="p-3 border-t border-border-light flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your trip..."
              disabled={sending}
              className="flex-1 border-2 border-border-heavy bg-paper px-3 py-2 text-sm font-body text-text-primary placeholder:text-text-ghost focus:outline-none focus:border-accent disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || sending}
              className="px-4 py-2 bg-contrast text-paper font-ui text-xs font-bold uppercase tracking-[0.1em] hover:bg-accent btn-transition min-h-touch disabled:opacity-50"
            >
              Send
            </button>
          </div>
        </>
      )}
    </div>
  );
}

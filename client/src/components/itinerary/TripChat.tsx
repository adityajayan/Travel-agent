"use client";

import { useState, useEffect, useRef } from "react";
import { ChevronDown, Send, MessageCircle } from "lucide-react";
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
    <div className="border border-gold-light/40 bg-white rounded-xl shadow-sm flex flex-col overflow-hidden">
      {/* Chat header */}
      <button
        className="bg-navy rounded-t-xl px-4 py-2.5 flex items-center justify-between w-full"
        onClick={() => setCollapsed(!collapsed)}
      >
        <div className="flex items-center gap-2">
          <span className="w-6 h-6 bg-cream rounded-md flex items-center justify-center flex-shrink-0">
            <MessageCircle className="h-3.5 w-3.5 text-navy" />
          </span>
          <span className="font-sans text-xs font-semibold text-cream">
            Chat with Concierge
          </span>
        </div>
        <ChevronDown
          className={`h-4 w-4 text-cream/50 transition-transform ${collapsed ? "" : "rotate-180"}`}
        />
      </button>

      {!collapsed && (
        <>
          {/* Messages area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 max-h-80 min-h-[200px] bg-cream">
            {messages.length === 0 && (
              <div className="text-center py-6">
                <p className="font-sans text-sm text-slate/60">
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
                  className={`max-w-[85%] px-3 py-2 rounded-lg ${
                    msg.role === "user"
                      ? "bg-navy text-cream"
                      : "bg-white border border-gold-light/40"
                  }`}
                >
                  <p className={`font-sans text-sm ${msg.role === "user" ? "" : "text-charcoal"}`}>
                    {msg.content}
                  </p>
                </div>
              </div>
            ))}
            {sending && (
              <div className="flex justify-start">
                <div className="bg-white border border-gold-light/40 px-3 py-2 rounded-lg">
                  <div className="flex gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-navy/20 animate-pulse-dot" />
                    <span className="h-2 w-2 rounded-full bg-navy/20 animate-pulse-dot" style={{ animationDelay: "0.3s" }} />
                    <span className="h-2 w-2 rounded-full bg-navy/20 animate-pulse-dot" style={{ animationDelay: "0.6s" }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick actions */}
          <div className="px-4 py-2 flex gap-2 flex-wrap border-t border-gold-light/30">
            {quickActions.map((action) => (
              <button
                key={action}
                onClick={() => setInput(action)}
                className="px-2.5 py-1 border border-gold rounded-md font-sans text-[0.6rem] font-medium text-gold hover:bg-gold/8 btn-transition"
              >
                {action}
              </button>
            ))}
          </div>

          {/* Input area */}
          <div className="p-3 border-t border-gold-light/30 flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your trip..."
              disabled={sending}
              className="flex-1 border border-navy/20 bg-cream rounded-md px-3 py-2 text-sm font-sans text-navy placeholder:text-slate/50 focus:outline-none focus:ring-2 focus:ring-gold/30 focus:border-gold disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || sending}
              className="px-4 py-2 bg-navy text-cream font-sans text-xs font-semibold rounded-md hover:bg-navy-light btn-transition min-h-touch disabled:opacity-50 flex items-center gap-1.5"
            >
              <Send className="h-3.5 w-3.5" />
              Send
            </button>
          </div>
        </>
      )}
    </div>
  );
}

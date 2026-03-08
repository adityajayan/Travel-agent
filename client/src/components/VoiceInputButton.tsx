"use client";

import { useState, useRef, useCallback } from "react";
import { Mic, StopCircle } from "lucide-react";

/* eslint-disable @typescript-eslint/no-explicit-any */
type SpeechRecognitionInstance = any;

interface VoiceInputButtonProps {
  onResult: (transcript: string) => void;
  disabled?: boolean;
}

export default function VoiceInputButton({ onResult, disabled }: VoiceInputButtonProps) {
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionInstance>(null);

  const isSupported = typeof window !== "undefined" && ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);

  const toggle = useCallback(() => {
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    const SpeechRecognitionCtor =
      (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition;

    if (!SpeechRecognitionCtor) return;

    const recognition = new SpeechRecognitionCtor();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      onResult(transcript);
      setListening(false);
    };

    recognition.onerror = () => {
      setListening(false);
    };

    recognition.onend = () => {
      setListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }, [listening, onResult]);

  if (!isSupported) return null;

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={disabled}
      aria-label={listening ? "Stop voice input" : "Start voice input"}
      className={`p-2.5 border rounded-md btn-transition ${
        listening
          ? "bg-gold/10 border-gold text-gold"
          : "bg-cream border-navy/20 text-charcoal hover:bg-cream-dark"
      } disabled:opacity-50 disabled:cursor-not-allowed`}
    >
      {listening ? (
        <StopCircle className="h-5 w-5" />
      ) : (
        <Mic className="h-5 w-5" />
      )}
    </button>
  );
}

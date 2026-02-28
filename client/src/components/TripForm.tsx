"use client";

import { useState } from "react";
import VoiceInputButton from "./VoiceInputButton";

interface TripFormProps {
  onSubmit: (goal: string) => void;
  disabled?: boolean;
}

export default function TripForm({ onSubmit, disabled }: TripFormProps) {
  const [goal, setGoal] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = goal.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
    setGoal("");
  };

  const handleVoiceResult = (transcript: string) => {
    setGoal(transcript);
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <label htmlFor="trip-goal" className="block text-sm font-medium text-gray-700 mb-2">
        Where would you like to go?
      </label>
      <div className="flex gap-2">
        <input
          id="trip-goal"
          type="text"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="e.g. 3-day trip to Paris with flights and hotel"
          className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          disabled={disabled}
        />
        <VoiceInputButton onResult={handleVoiceResult} disabled={disabled} />
        <button
          type="submit"
          disabled={disabled || !goal.trim()}
          className="px-5 py-2.5 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Plan Trip
        </button>
      </div>
    </form>
  );
}

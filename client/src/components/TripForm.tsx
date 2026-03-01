"use client";

import { useState } from "react";
import VoiceInputButton from "./VoiceInputButton";
import { CreateTripOptions } from "@/lib/api";

interface TripFormProps {
  onSubmit: (options: CreateTripOptions) => void;
  disabled?: boolean;
}

export default function TripForm({ onSubmit, disabled }: TripFormProps) {
  const [destination, setDestination] = useState("");
  const [duration, setDuration] = useState("");
  const [airline, setAirline] = useState("");
  const [stayType, setStayType] = useState("");
  const [budget, setBudget] = useState("");
  const [notes, setNotes] = useState("");

  const buildGoal = (): string => {
    const parts: string[] = [];

    if (duration.trim()) {
      parts.push(`${duration.trim()} trip`);
    } else {
      parts.push("Trip");
    }

    if (destination.trim()) {
      parts.push(`to ${destination.trim()}`);
    }

    if (airline.trim()) {
      parts.push(`flying ${airline.trim()}`);
    } else {
      parts.push("with flights");
    }

    if (stayType.trim()) {
      parts.push(`staying at a ${stayType.trim()}`);
    } else {
      parts.push("and hotel");
    }

    if (budget.trim()) {
      parts.push(`with a budget of $${budget.trim()}`);
    }

    if (notes.trim()) {
      parts.push(`— ${notes.trim()}`);
    }

    return parts.join(" ");
  };

  const canSubmit = destination.trim().length > 0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    const goal = buildGoal();
    const options: CreateTripOptions = { goal };
    if (budget) options.total_budget = parseFloat(budget);

    onSubmit(options);
    setDestination("");
    setDuration("");
    setAirline("");
    setStayType("");
    setBudget("");
    setNotes("");
  };

  const handleVoiceResult = (transcript: string) => {
    // Voice input goes into the notes/free-text field
    setNotes(transcript);
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <label className="block text-sm font-medium text-gray-700 mb-4">
        Plan your trip
      </label>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
        <div>
          <label htmlFor="destination" className="block text-xs font-medium text-gray-600 mb-1">
            Where to? *
          </label>
          <input
            id="destination"
            type="text"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            placeholder="e.g. Paris, Tokyo, New York"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            disabled={disabled}
          />
        </div>
        <div>
          <label htmlFor="duration" className="block text-xs font-medium text-gray-600 mb-1">
            How long?
          </label>
          <input
            id="duration"
            type="text"
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            placeholder="e.g. 3 days, 1 week"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            disabled={disabled}
          />
        </div>
        <div>
          <label htmlFor="airline" className="block text-xs font-medium text-gray-600 mb-1">
            Airline preference
          </label>
          <input
            id="airline"
            type="text"
            value={airline}
            onChange={(e) => setAirline(e.target.value)}
            placeholder="e.g. Delta, United, any"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            disabled={disabled}
          />
        </div>
        <div>
          <label htmlFor="stay" className="block text-xs font-medium text-gray-600 mb-1">
            Stay preference
          </label>
          <input
            id="stay"
            type="text"
            value={stayType}
            onChange={(e) => setStayType(e.target.value)}
            placeholder="e.g. hotel, Airbnb, hostel"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            disabled={disabled}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
        <div>
          <label htmlFor="budget" className="block text-xs font-medium text-gray-600 mb-1">
            Budget ($)
          </label>
          <input
            id="budget"
            type="number"
            min="0"
            step="0.01"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
            placeholder="No limit"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            disabled={disabled}
          />
        </div>
        <div>
          <label htmlFor="notes" className="block text-xs font-medium text-gray-600 mb-1">
            Anything else?
          </label>
          <div className="flex gap-2">
            <input
              id="notes"
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. business class, pet-friendly"
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              disabled={disabled}
            />
            <VoiceInputButton onResult={handleVoiceResult} disabled={disabled} />
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-400">
          Leave any field blank and the agents will figure out the best options for you.
        </p>
        <button
          type="submit"
          disabled={disabled || !canSubmit}
          className="px-5 py-2.5 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Plan Trip
        </button>
      </div>
    </form>
  );
}

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
    setNotes(transcript);
  };

  const inputClasses = "w-full border-2 border-border-heavy bg-paper px-3 py-2.5 text-sm font-body text-text-primary placeholder:text-text-ghost focus:outline-none focus:border-accent disabled:opacity-50 disabled:cursor-not-allowed";

  return (
    <form onSubmit={handleSubmit} className="bg-white border-2 border-border-heavy p-4 lg:p-6 card-hover-bar">
      <p className="eyebrow mb-4">Plan Your Trip</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
        <div>
          <label htmlFor="destination" className="block font-body text-xs font-medium text-text-mid mb-1">
            Where to? *
          </label>
          <input
            id="destination"
            type="text"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            placeholder="e.g. Paris, Tokyo, New York"
            className={inputClasses}
            disabled={disabled}
          />
        </div>
        <div>
          <label htmlFor="duration" className="block font-body text-xs font-medium text-text-mid mb-1">
            How long?
          </label>
          <input
            id="duration"
            type="text"
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            placeholder="e.g. 3 days, 1 week"
            className={inputClasses}
            disabled={disabled}
          />
        </div>
        <div>
          <label htmlFor="airline" className="block font-body text-xs font-medium text-text-mid mb-1">
            Airline preference
          </label>
          <input
            id="airline"
            type="text"
            value={airline}
            onChange={(e) => setAirline(e.target.value)}
            placeholder="e.g. Delta, United, any"
            className={inputClasses}
            disabled={disabled}
          />
        </div>
        <div>
          <label htmlFor="stay" className="block font-body text-xs font-medium text-text-mid mb-1">
            Stay preference
          </label>
          <input
            id="stay"
            type="text"
            value={stayType}
            onChange={(e) => setStayType(e.target.value)}
            placeholder="e.g. hotel, Airbnb, hostel"
            className={inputClasses}
            disabled={disabled}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
        <div>
          <label htmlFor="budget" className="block font-body text-xs font-medium text-text-mid mb-1">
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
            className={inputClasses}
            disabled={disabled}
          />
        </div>
        <div>
          <label htmlFor="notes" className="block font-body text-xs font-medium text-text-mid mb-1">
            Anything else?
          </label>
          <div className="flex gap-2">
            <input
              id="notes"
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. business class, pet-friendly"
              className={`flex-1 ${inputClasses}`}
              disabled={disabled}
            />
            <VoiceInputButton onResult={handleVoiceResult} disabled={disabled} />
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 pt-3 border-t border-border-light">
        <p className="text-xs text-text-ghost font-body font-light hidden sm:block">
          Leave any field blank and the agents will figure out the best options for you.
        </p>
        <button
          type="submit"
          disabled={disabled || !canSubmit}
          className="w-full sm:w-auto px-6 py-3 lg:py-2.5 bg-contrast text-paper font-ui text-xs font-bold uppercase tracking-[0.1em] hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed btn-transition min-h-touch"
        >
          Plan Trip
        </button>
      </div>
    </form>
  );
}

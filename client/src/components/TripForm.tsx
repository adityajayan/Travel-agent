"use client";

import { useState } from "react";
import VoiceInputButton from "./VoiceInputButton";
import { CreateTripOptions } from "@/lib/api";

interface TripFormProps {
  onSubmit: (options: CreateTripOptions) => void;
  disabled?: boolean;
}

export default function TripForm({ onSubmit, disabled }: TripFormProps) {
  const [goal, setGoal] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [budget, setBudget] = useState("");
  const [orgId, setOrgId] = useState("");
  const [policyId, setPolicyId] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = goal.trim();
    if (!trimmed) return;

    const options: CreateTripOptions = { goal: trimmed };
    if (budget) options.total_budget = parseFloat(budget);
    if (orgId.trim()) options.org_id = orgId.trim();
    if (policyId.trim()) options.policy_id = policyId.trim();

    onSubmit(options);
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

      <button
        type="button"
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="mt-3 text-xs text-gray-500 hover:text-gray-700 transition-colors"
      >
        {showAdvanced ? "Hide" : "Show"} advanced options
      </button>

      {showAdvanced && (
        <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-3">
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
              placeholder="e.g. 2000"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              disabled={disabled}
            />
          </div>
          <div>
            <label htmlFor="org-id" className="block text-xs font-medium text-gray-600 mb-1">
              Organization ID
            </label>
            <input
              id="org-id"
              type="text"
              value={orgId}
              onChange={(e) => setOrgId(e.target.value)}
              placeholder="e.g. acme-corp"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              disabled={disabled}
            />
          </div>
          <div>
            <label htmlFor="policy-id" className="block text-xs font-medium text-gray-600 mb-1">
              Policy ID
            </label>
            <input
              id="policy-id"
              type="text"
              value={policyId}
              onChange={(e) => setPolicyId(e.target.value)}
              placeholder="e.g. policy-123"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              disabled={disabled}
            />
          </div>
        </div>
      )}
    </form>
  );
}

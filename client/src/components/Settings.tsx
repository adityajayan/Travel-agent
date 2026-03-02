"use client";

import { useState, useEffect } from "react";

interface SettingsProps {
  onClose: () => void;
}

interface StoredPreferences {
  orgId: string;
  policyId: string;
  defaultDepartureCity: string;
  preferredAirlines: string;
  preferredHotelChains: string;
  cabinClass: string;
  loyaltyPrograms: string;
  dietaryNeeds: string;
  accessibilityNeeds: string;
}

const STORAGE_KEY = "travel_agent_preferences";

function loadPreferences(): StoredPreferences {
  if (typeof window === "undefined") return defaultPrefs();
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...defaultPrefs(), ...JSON.parse(raw) };
  } catch { /* ignore */ }
  return defaultPrefs();
}

function defaultPrefs(): StoredPreferences {
  return {
    orgId: "",
    policyId: "",
    defaultDepartureCity: "",
    preferredAirlines: "",
    preferredHotelChains: "",
    cabinClass: "economy",
    loyaltyPrograms: "",
    dietaryNeeds: "",
    accessibilityNeeds: "",
  };
}

export default function Settings({ onClose }: SettingsProps) {
  const [prefs, setPrefs] = useState<StoredPreferences>(defaultPrefs());
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setPrefs(loadPreferences());
  }, []);

  const update = (key: keyof StoredPreferences, value: string) => {
    setPrefs((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  };

  const handleSave = () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-gray-900">Settings & Preferences</h2>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 transition-colors"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="space-y-6">
        {/* Organization */}
        <section>
          <h3 className="text-sm font-medium text-gray-700 mb-3">Organization</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Organization ID</label>
              <input
                type="text"
                value={prefs.orgId}
                onChange={(e) => update("orgId", e.target.value)}
                placeholder="e.g. org-acme-corp"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Policy ID (optional)</label>
              <input
                type="text"
                value={prefs.policyId}
                onChange={(e) => update("policyId", e.target.value)}
                placeholder="Auto-resolved from org"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
          </div>
        </section>

        {/* Travel defaults */}
        <section>
          <h3 className="text-sm font-medium text-gray-700 mb-3">Travel Defaults</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Home City</label>
              <input
                type="text"
                value={prefs.defaultDepartureCity}
                onChange={(e) => update("defaultDepartureCity", e.target.value)}
                placeholder="e.g. New York, San Francisco"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Cabin Class</label>
              <select
                value={prefs.cabinClass}
                onChange={(e) => update("cabinClass", e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white"
              >
                <option value="economy">Economy</option>
                <option value="premium_economy">Premium Economy</option>
                <option value="business">Business</option>
                <option value="first">First Class</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Preferred Airlines</label>
              <input
                type="text"
                value={prefs.preferredAirlines}
                onChange={(e) => update("preferredAirlines", e.target.value)}
                placeholder="e.g. Delta, United"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Preferred Hotels</label>
              <input
                type="text"
                value={prefs.preferredHotelChains}
                onChange={(e) => update("preferredHotelChains", e.target.value)}
                placeholder="e.g. Marriott, Hilton"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
          </div>
        </section>

        {/* Loyalty & accessibility */}
        <section>
          <h3 className="text-sm font-medium text-gray-700 mb-3">Personal</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Loyalty Programs</label>
              <input
                type="text"
                value={prefs.loyaltyPrograms}
                onChange={(e) => update("loyaltyPrograms", e.target.value)}
                placeholder="e.g. SkyMiles #12345, Marriott Bonvoy"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Dietary Requirements</label>
              <input
                type="text"
                value={prefs.dietaryNeeds}
                onChange={(e) => update("dietaryNeeds", e.target.value)}
                placeholder="e.g. vegetarian, gluten-free"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">Accessibility Needs</label>
              <input
                type="text"
                value={prefs.accessibilityNeeds}
                onChange={(e) => update("accessibilityNeeds", e.target.value)}
                placeholder="e.g. wheelchair accessible, ground floor rooms"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
          </div>
        </section>
      </div>

      <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-100">
        <p className="text-xs text-gray-400">Saved locally in your browser</p>
        <div className="flex items-center gap-3">
          {saved && <span className="text-xs text-green-600 font-medium">Saved!</span>}
          <button
            onClick={handleSave}
            className="px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 transition-colors"
          >
            Save Preferences
          </button>
        </div>
      </div>
    </div>
  );
}

// Helper to get saved preferences for trip creation
export function getSavedPreferences(): Partial<{ orgId: string; policyId: string; departureCity: string; cabinClass: string }> {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const prefs = JSON.parse(raw);
    return {
      orgId: prefs.orgId || undefined,
      policyId: prefs.policyId || undefined,
      departureCity: prefs.defaultDepartureCity || undefined,
      cabinClass: prefs.cabinClass || undefined,
    };
  } catch {
    return {};
  }
}

"use client";

import { useState, useEffect } from "react";
import { X } from "lucide-react";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import FormInput from "@/components/ui/FormInput";

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

const selectClasses = "w-full border border-navy/20 bg-cream rounded-md px-3 py-2 text-sm font-sans text-navy focus:outline-none focus:ring-2 focus:ring-gold/30 focus:border-gold";

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
    <Card padding="md">
      <div className="flex items-center justify-between mb-6">
        <h2 className="font-serif text-xl font-medium text-navy">Settings & Preferences</h2>
        <button
          onClick={onClose}
          className="text-slate hover:text-navy btn-transition p-2 -mr-2 min-h-touch min-w-touch flex items-center justify-center rounded-md hover:bg-cream-dark focus:outline-none focus:ring-2 focus:ring-gold/30"
          aria-label="Close settings"
        >
          <X className="h-5 w-5" aria-hidden="true" />
        </button>
      </div>

      <div className="space-y-6">
        <section>
          <p className="eyebrow mb-3">Organization</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <FormInput
              label="Organization ID"
              value={prefs.orgId}
              onChange={(e) => update("orgId", e.target.value)}
              placeholder="e.g. org-acme-corp"
            />
            <FormInput
              label="Policy ID (optional)"
              value={prefs.policyId}
              onChange={(e) => update("policyId", e.target.value)}
              placeholder="Auto-resolved from org"
            />
          </div>
        </section>

        <section>
          <p className="eyebrow mb-3">Travel Defaults</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <FormInput
              label="Home City"
              value={prefs.defaultDepartureCity}
              onChange={(e) => update("defaultDepartureCity", e.target.value)}
              placeholder="e.g. New York, San Francisco"
            />
            <div>
              <label className="block font-sans text-xs font-medium text-charcoal mb-1">Cabin Class</label>
              <select
                value={prefs.cabinClass}
                onChange={(e) => update("cabinClass", e.target.value)}
                className={selectClasses}
              >
                <option value="economy">Economy</option>
                <option value="premium_economy">Premium Economy</option>
                <option value="business">Business</option>
                <option value="first">First Class</option>
              </select>
            </div>
            <FormInput
              label="Preferred Airlines"
              value={prefs.preferredAirlines}
              onChange={(e) => update("preferredAirlines", e.target.value)}
              placeholder="e.g. Delta, United"
            />
            <FormInput
              label="Preferred Hotels"
              value={prefs.preferredHotelChains}
              onChange={(e) => update("preferredHotelChains", e.target.value)}
              placeholder="e.g. Marriott, Hilton"
            />
          </div>
        </section>

        <section>
          <p className="eyebrow mb-3">Personal</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <FormInput
              label="Loyalty Programs"
              value={prefs.loyaltyPrograms}
              onChange={(e) => update("loyaltyPrograms", e.target.value)}
              placeholder="e.g. SkyMiles #12345, Marriott Bonvoy"
            />
            <FormInput
              label="Dietary Requirements"
              value={prefs.dietaryNeeds}
              onChange={(e) => update("dietaryNeeds", e.target.value)}
              placeholder="e.g. vegetarian, gluten-free"
            />
            <div className="sm:col-span-2">
              <FormInput
                label="Accessibility Needs"
                value={prefs.accessibilityNeeds}
                onChange={(e) => update("accessibilityNeeds", e.target.value)}
                placeholder="e.g. wheelchair accessible, ground floor rooms"
              />
            </div>
          </div>
        </section>
      </div>

      <div className="flex items-center justify-between mt-6 pt-4 border-t border-gold-light/30">
        <p className="font-sans text-xs text-slate/60">Saved locally in your browser</p>
        <div className="flex items-center gap-3">
          {saved && <span className="font-sans text-xs text-success font-semibold">Saved</span>}
          <Button variant="primary" size="md" onClick={handleSave}>
            Save Preferences
          </Button>
        </div>
      </div>
    </Card>
  );
}

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

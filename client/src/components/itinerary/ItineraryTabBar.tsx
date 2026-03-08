"use client";

interface ItineraryTabBarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const tabs = [
  { id: "itinerary", label: "Itinerary" },
  { id: "map", label: "Map" },
  { id: "documents", label: "Documents" },
  { id: "history", label: "History" },
];

export default function ItineraryTabBar({ activeTab, onTabChange }: ItineraryTabBarProps) {
  return (
    <div className="flex gap-0 border border-navy/20 rounded-lg overflow-hidden mb-6">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`flex-1 px-4 py-2.5 font-sans text-xs font-semibold btn-transition ${
            activeTab === tab.id
              ? "bg-navy text-cream"
              : "text-slate hover:text-navy hover:bg-cream-dark"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

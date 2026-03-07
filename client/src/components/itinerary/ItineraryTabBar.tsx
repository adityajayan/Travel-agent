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
    <div className="flex gap-0 border-2 border-border-heavy mb-6">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`flex-1 px-4 py-2.5 font-ui text-[0.72rem] font-bold uppercase tracking-[0.1em] btn-transition ${
            activeTab === tab.id
              ? "bg-contrast text-paper"
              : "text-text-muted hover:text-contrast hover:bg-paper-elevated"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

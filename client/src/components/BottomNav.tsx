"use client";

import { List, Plus, Zap, Settings } from "lucide-react";

interface BottomNavProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  tripCount?: number;
  hasActiveTrip?: boolean;
}

export default function BottomNav({ activeTab, onTabChange, tripCount, hasActiveTrip }: BottomNavProps) {
  const tabs = [
    { id: "trips", label: "Trips", icon: List, badge: tripCount },
    { id: "plan", label: "Plan", icon: Plus },
    { id: "timeline", label: "Live", icon: Zap, dot: hasActiveTrip },
    { id: "settings", label: "Settings", icon: Settings },
  ];

  return (
    <nav className="btm-nav fixed bottom-0 left-0 right-0 z-50 bg-cream/90 backdrop-blur-md border-t border-gold-light/40 lg:hidden safe-area-bottom">
      <div className="flex items-stretch justify-around h-full">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`flex-1 flex flex-col items-center justify-center gap-0.5 py-2 min-h-touch relative btn-transition ${
                isActive ? "text-navy" : "text-slate/60"
              }`}
            >
              <div className="relative">
                <Icon className="h-5 w-5" strokeWidth={1.5} />
                {tab.badge != null && tab.badge > 0 && (
                  <span className="absolute -top-1 -right-1.5 h-4 min-w-[1rem] flex items-center justify-center bg-navy text-cream text-[10px] font-sans font-semibold px-1 rounded-full">
                    {tab.badge > 99 ? "99+" : tab.badge}
                  </span>
                )}
                {tab.dot && (
                  <span className="absolute -top-0.5 -right-0.5 h-2 w-2 bg-gold rounded-full animate-pulse-dot" />
                )}
              </div>
              <span className="font-sans text-[10px] font-medium tracking-wide">{tab.label}</span>
              {isActive && (
                <span className="absolute top-0 left-1/2 -translate-x-1/2 h-[2px] w-8 bg-gold rounded-full" />
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
}

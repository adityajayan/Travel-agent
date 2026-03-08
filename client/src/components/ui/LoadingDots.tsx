"use client";

interface LoadingDotsProps {
  label?: string;
  className?: string;
}

export default function LoadingDots({ label, className = "" }: LoadingDotsProps) {
  return (
    <div className={`text-center py-8 ${className}`}>
      <div className="flex justify-center gap-1.5 mb-3">
        <span className="h-2 w-2 rounded-full bg-navy/20 animate-pulse-dot" />
        <span className="h-2 w-2 rounded-full bg-navy/20 animate-pulse-dot" style={{ animationDelay: "0.3s" }} />
        <span className="h-2 w-2 rounded-full bg-navy/20 animate-pulse-dot" style={{ animationDelay: "0.6s" }} />
      </div>
      {label && (
        <p className="font-sans text-sm text-slate/60">{label}</p>
      )}
    </div>
  );
}

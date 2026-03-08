"use client";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: "none" | "sm" | "md";
  hover?: boolean;
}

const paddingClasses = {
  none: "",
  sm: "p-4",
  md: "p-6",
};

export default function Card({ children, className = "", padding = "sm", hover }: CardProps) {
  return (
    <div
      className={`border border-gold-light/40 bg-white rounded-xl shadow-sm ${hover ? "card-hover-bar" : ""} ${paddingClasses[padding]} ${className}`}
    >
      {children}
    </div>
  );
}

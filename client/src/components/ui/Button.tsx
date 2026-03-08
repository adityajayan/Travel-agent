"use client";

import { forwardRef } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-navy text-cream hover:bg-navy-light disabled:opacity-50 disabled:cursor-not-allowed",
  secondary:
    "text-charcoal border border-navy/20 hover:bg-navy hover:text-cream disabled:opacity-50 disabled:cursor-not-allowed",
  ghost:
    "text-slate hover:text-navy disabled:opacity-50 disabled:cursor-not-allowed",
  danger:
    "text-error border border-error hover:bg-error/5 disabled:opacity-50 disabled:cursor-not-allowed",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-5 py-2.5 text-sm",
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", size = "sm", loading, className = "", disabled, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={`font-sans font-semibold rounded-md btn-transition min-h-touch focus:outline-none focus:ring-2 focus:ring-gold/30 focus:ring-offset-1 ${variantClasses[variant]} ${sizeClasses[size]} ${loading ? "animate-pulse" : ""} ${className}`}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";

export default Button;

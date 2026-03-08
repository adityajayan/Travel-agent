"use client";

import { forwardRef, useId } from "react";

interface FormInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  required?: boolean;
  error?: string;
  hint?: string;
}

const FormInput = forwardRef<HTMLInputElement, FormInputProps>(
  ({ label, required, error, hint, className = "", id: externalId, ...props }, ref) => {
    const generatedId = useId();
    const inputId = externalId || generatedId;
    const errorId = error ? `${inputId}-error` : undefined;
    const hintId = hint ? `${inputId}-hint` : undefined;
    const describedBy = [errorId, hintId].filter(Boolean).join(" ") || undefined;

    return (
      <div>
        <label htmlFor={inputId} className="block font-sans text-xs font-medium text-charcoal mb-1">
          {label}
          {required && <span className="text-error ml-0.5" aria-label="required">*</span>}
        </label>
        <input
          ref={ref}
          id={inputId}
          aria-required={required}
          aria-invalid={!!error}
          aria-describedby={describedBy}
          className={`w-full border bg-cream rounded-md px-3 py-2 text-sm font-sans text-navy placeholder:text-slate/50 focus:outline-none focus:ring-2 focus:ring-gold/30 focus:border-gold ${
            error ? "border-error ring-1 ring-error/30" : "border-navy/20"
          } ${className}`}
          {...props}
        />
        {error && (
          <p id={errorId} className="font-sans text-xs text-error mt-0.5">{error}</p>
        )}
        {hint && !error && (
          <p id={hintId} className="font-sans text-xs text-slate/60 mt-0.5">{hint}</p>
        )}
      </div>
    );
  }
);

FormInput.displayName = "FormInput";

export default FormInput;

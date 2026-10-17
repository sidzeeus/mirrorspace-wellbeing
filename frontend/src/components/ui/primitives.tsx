/**
 * Small building blocks with no client-side state, usable from server components.
 * Styling comes from the classes in globals.css so both themes are covered once.
 */
import type {
  ButtonHTMLAttributes,
  HTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  Ref,
} from "react";

type Variant = "primary" | "quiet" | "care" | "text";

const VARIANT_CLASS: Record<Variant, string> = {
  primary: "btn btn-primary",
  quiet: "btn btn-quiet",
  care: "btn btn-care",
  text: "btn-text",
};

export function buttonClass(variant: Variant = "primary", extra = ""): string {
  return `${VARIANT_CLASS[variant]} ${extra}`.trim();
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  /** Shows that the action is in progress and blocks a second press. */
  busy?: boolean;
};

export function Button({ variant = "primary", busy, className, children, ...props }: ButtonProps) {
  return (
    <button
      type="button"
      {...props}
      disabled={props.disabled || busy}
      aria-busy={busy || undefined}
      className={buttonClass(variant, className)}
    >
      {children}
    </button>
  );
}

type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  /** Required: the icon alone says nothing to a screen reader. */
  label: string;
};

export function IconButton({ label, className = "", children, ...props }: IconButtonProps) {
  return (
    <button
      type="button"
      {...props}
      aria-label={label}
      title={label}
      className={`inline-flex h-11 w-11 items-center justify-center rounded-full border border-line-strong text-moon hover:bg-raised ${className}`}
    >
      <span aria-hidden="true">{children}</span>
    </button>
  );
}

type PanelProps = HTMLAttributes<HTMLDivElement> & {
  /** Crop marks outside the corners. Reserved for the three framed stages. */
  marks?: boolean;
};

export function Panel({ marks, className = "", ...props }: PanelProps) {
  return <div {...props} className={`frame ${marks ? "marks" : ""} ${className}`} />;
}

export function GlassPanel({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div {...props} className={`glass ${className}`} />;
}

export function VisuallyHidden({ children }: { children: ReactNode }) {
  return <span className="sr-only">{children}</span>;
}

export function SkipLink({ children }: { children: ReactNode }) {
  return (
    <a
      href="#main"
      className="btn btn-primary sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50"
    >
      {children}
    </a>
  );
}

type FieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  /** Short guidance shown under the label. */
  hint?: string;
  /** What is wrong and how to fix it. */
  error?: string;
  ref?: Ref<HTMLInputElement>;
};

/** A labelled input. The label, hint and error are all tied to the control. */
export function Field({ label, hint, error, id, className = "", ref, ...props }: FieldProps) {
  const inputId = id ?? props.name ?? label;
  const hintId = hint ? `${inputId}-hint` : undefined;
  const errorId = error ? `${inputId}-error` : undefined;
  return (
    <div className={className}>
      <label htmlFor={inputId} className="mb-1.5 block font-medium">
        {label}
      </label>
      {hint ? (
        <p id={hintId} className="mb-1.5 text-sm text-dim">
          {hint}
        </p>
      ) : null}
      <input
        {...props}
        ref={ref}
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={[hintId, errorId].filter(Boolean).join(" ") || undefined}
        className="control"
      />
      {error ? (
        <p id={errorId} role="alert" className="mt-1.5 text-sm text-warm">
          {error}
        </p>
      ) : null}
    </div>
  );
}

/** A circular progress indicator: the reduced-motion stand-in for the breathing pet. */
export function ProgressRing({
  value,
  label,
  size = 160,
  children,
}: {
  /** 0 to 1. */
  value: number;
  label: string;
  size?: number;
  children?: ReactNode;
}) {
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(1, value));
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(clamped * 100)}
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <svg viewBox="0 0 100 100" className="absolute inset-0 -rotate-90" aria-hidden="true">
        <circle cx="50" cy="50" r={radius} fill="none" stroke="var(--line)" strokeWidth="3" />
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke="var(--accent)"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - clamped)}
        />
      </svg>
      <div className="relative text-center">{children}</div>
    </div>
  );
}

/** Marks content a qualified reviewer has not signed off. Development builds only. */
export function UnreviewedBadge({ children }: { children: ReactNode }) {
  return (
    <span className="data inline-block rounded-full border border-warm px-2 py-0.5 text-warm">
      {children}
    </span>
  );
}

/** A calm, inline status line. `tone` picks the color; the words carry the meaning. */
export function Notice({
  tone = "info",
  children,
  role,
}: {
  tone?: "info" | "saved" | "attention";
  children: ReactNode;
  role?: "status" | "alert";
}) {
  const color = tone === "saved" ? "border-calm" : tone === "attention" ? "border-warm" : "border-line-strong";
  return (
    <div role={role} className={`rounded-[14px] border-l-2 ${color} bg-surface px-4 py-3`}>
      {children}
    </div>
  );
}

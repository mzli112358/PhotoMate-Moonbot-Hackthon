import type { ReactNode } from "react";

export interface OptionCardProps {
  eyebrow?: string;
  title: string;
  description?: string;
  hint?: string;
  selected?: boolean;
  dimmed?: boolean;
  icon?: ReactNode;
  children?: ReactNode;
  className?: string;
  compact?: boolean;
  onClick?: () => void;
}

export function OptionCard({
  eyebrow,
  title,
  description,
  hint,
  selected = false,
  dimmed = false,
  icon,
  children,
  className = "",
  compact = false,
  onClick,
}: OptionCardProps) {
  const clickable = typeof onClick === "function";
  return (
    <div
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : undefined}
      onClick={onClick}
      onKeyDown={
        clickable
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
      className={`relative flex flex-col rounded-[28px] border bg-card transition-all duration-300 ${
        compact ? "p-5" : "p-8"
      } ${
        selected
          ? "border-robot-orange bg-robot-orange-soft/60 shadow-[0_30px_80px_-40px_var(--robot-orange-glow)]"
          : "border-robot-hairline shadow-[0_20px_50px_-40px_rgba(20,15,10,0.35)]"
      } ${dimmed ? "opacity-60" : "opacity-100"} ${
        clickable
          ? "cursor-pointer hover:-translate-y-0.5 hover:border-robot-orange/60 hover:shadow-[0_28px_70px_-40px_var(--robot-orange-glow)] focus:outline-none focus-visible:ring-2 focus-visible:ring-robot-orange"
          : ""
      } ${className}`}
    >
      {selected && (
        <span className="absolute right-5 top-5 inline-flex items-center gap-1.5 rounded-full bg-robot-orange px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-white">
          <span className="h-1.5 w-1.5 rounded-full bg-white" />
          Selected
        </span>
      )}

      {icon && (
        <div
          className={`mb-5 flex items-center justify-center rounded-2xl transition-colors ${
            compact ? "h-14 w-14" : "h-20 w-20"
          } ${
            selected
              ? "bg-robot-orange text-white"
              : "bg-robot-surface text-robot-ink"
          }`}
        >
          {icon}
        </div>
      )}

      {eyebrow && (
        <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.24em] text-robot-muted">
          {eyebrow}
        </div>
      )}

      <h3
        className={`font-display font-medium text-robot-ink ${
          compact ? "text-lg" : "text-2xl"
        }`}
      >
        {title}
      </h3>

      {description && (
        <p
          className={`mt-2 text-robot-muted ${compact ? "text-[13px]" : "text-sm leading-relaxed"}`}
        >
          {description}
        </p>
      )}

      {children}

      {hint && (
        <div className="mt-6 flex items-center gap-2 border-t border-robot-hairline pt-4">
          <span className="flex h-5 w-5 items-center justify-center rounded-full border border-robot-hairline">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 2a4 4 0 0 0-4 4v6a4 4 0 0 0 8 0V6a4 4 0 0 0-4-4z"
                stroke="currentColor"
                strokeWidth="2"
              />
              <path
                d="M5 11a7 7 0 0 0 14 0M12 18v3"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </span>
          <span className="text-[11px] font-medium tracking-wide text-robot-muted">
            说 <span className="text-robot-ink">“{hint}”</span>
          </span>
        </div>
      )}
    </div>
  );
}

"use client";

/**
 * Interactive controls built on Radix primitives, which supply keyboard handling,
 * focus management and ARIA. Every target is at least 44px.
 */
import {
  Dialog as RadixDialog,
  Slider as RadixSlider,
  Switch as RadixSwitch,
  Tabs as RadixTabs,
  Toast as RadixToast,
} from "radix-ui";
import {
  type ReactNode,
  createContext,
  useCallback,
  useContext,
  useId,
  useMemo,
  useState,
} from "react";

import { buttonClass } from "./primitives";

type SliderProps = {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  /** Words for the current value, read by screen readers and shown beside the label. */
  valueText: string;
  minLabel?: string;
  maxLabel?: string;
};

export function Slider({
  label,
  value,
  onChange,
  min = 1,
  max = 5,
  step = 1,
  valueText,
  minLabel,
  maxLabel,
}: SliderProps) {
  const id = useId();
  return (
    <div>
      <div className="mb-3 flex items-baseline justify-between gap-4">
        <span id={id} className="font-medium">
          {label}
        </span>
        <span className="text-dim" aria-hidden="true">
          {valueText}
        </span>
      </div>
      <RadixSlider.Root
        className="relative flex h-11 w-full touch-none select-none items-center"
        value={[value]}
        min={min}
        max={max}
        step={step}
        onValueChange={([next]) => next !== undefined && onChange(next)}
      >
        <RadixSlider.Track className="relative h-1 grow rounded-full bg-line-strong">
          <RadixSlider.Range className="absolute h-full rounded-full bg-accent" />
        </RadixSlider.Track>
        <RadixSlider.Thumb
          aria-labelledby={id}
          aria-valuetext={valueText}
          className="block h-7 w-7 rounded-full border-2 border-ink bg-accent-hi"
        />
      </RadixSlider.Root>
      {minLabel || maxLabel ? (
        <div className="mt-1 flex justify-between text-sm text-dim" aria-hidden="true">
          <span>{minLabel}</span>
          <span>{maxLabel}</span>
        </div>
      ) : null}
    </div>
  );
}

export function Toggle({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  const id = useId();
  return (
    <div className="flex min-h-11 items-center justify-between gap-4">
      <label htmlFor={id} className="grow cursor-pointer py-2">
        <span className="block font-medium">{label}</span>
        {hint ? <span className="block text-sm text-dim">{hint}</span> : null}
      </label>
      <RadixSwitch.Root
        id={id}
        checked={checked}
        onCheckedChange={onChange}
        className="relative h-8 w-14 shrink-0 rounded-full border border-line-strong bg-surface data-[state=checked]:border-accent-hi data-[state=checked]:bg-accent-hi"
      >
        <RadixSwitch.Thumb className="block h-6 w-6 translate-x-1 rounded-full bg-dim transition-transform data-[state=checked]:translate-x-7 data-[state=checked]:bg-on-accent" />
      </RadixSwitch.Root>
    </div>
  );
}

/** A 1-to-N choice as large buttons: sleep quality, energy, stress, intensity. */
export function ScaleControl({
  label,
  value,
  onChange,
  options,
  clearLabel,
}: {
  label: string;
  value: number | null;
  onChange: (value: number | null) => void;
  /** One entry per step, in order. `name` is the spoken meaning of that step. */
  options: readonly { value: number; name: string }[];
  /** Text for the control that removes the answer, so skipping is always possible. */
  clearLabel: string;
}) {
  const id = useId();
  return (
    <fieldset>
      <legend id={id} className="mb-2 flex w-full items-baseline justify-between gap-4">
        <span className="font-medium">{label}</span>
        <span className="text-sm text-dim" aria-live="polite">
          {options.find((option) => option.value === value)?.name ?? ""}
        </span>
      </legend>
      <div className="flex gap-2">
        {options.map((option) => {
          const selected = option.value === value;
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={selected}
              aria-label={`${option.value}: ${option.name}`}
              onClick={() => onChange(selected ? null : option.value)}
              className={`data h-12 grow rounded-[14px] border ${
                selected
                  ? "border-accent-hi bg-accent-hi text-on-accent"
                  : "border-line-strong bg-surface text-moon hover:bg-raised"
              }`}
            >
              {option.value}
            </button>
          );
        })}
      </div>
      {value !== null ? (
        <button type="button" className="btn-text text-sm" onClick={() => onChange(null)}>
          {clearLabel}
        </button>
      ) : null}
    </fieldset>
  );
}

export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 z-40 bg-ink/80" />
        <RadixDialog.Content className="fixed inset-x-4 top-1/2 z-50 mx-auto max-h-[85dvh] max-w-lg -translate-y-1/2 overflow-y-auto border border-line-strong bg-raised p-6">
          <RadixDialog.Title className="h2 mb-2">{title}</RadixDialog.Title>
          {description ? (
            <RadixDialog.Description className="mb-5 text-dim">{description}</RadixDialog.Description>
          ) : null}
          {children}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}

export function Tabs({
  label,
  tabs,
  value,
  onValueChange,
}: {
  label: string;
  tabs: readonly { id: string; title: string; content: ReactNode }[];
  /** The open tab, when the page keeps track of it (for example in the address). */
  value?: string;
  onValueChange?: (value: string) => void;
}) {
  return (
    <RadixTabs.Root
      {...(value !== undefined ? { value, onValueChange } : { defaultValue: tabs[0]?.id })}
    >
      <RadixTabs.List aria-label={label} className="mb-6 flex gap-1 border-b border-line">
        {tabs.map((tab) => (
          <RadixTabs.Trigger
            key={tab.id}
            value={tab.id}
            className="-mb-px min-h-11 border-b-2 border-transparent px-4 text-dim data-[state=active]:border-accent-hi data-[state=active]:text-moon"
          >
            {tab.title}
          </RadixTabs.Trigger>
        ))}
      </RadixTabs.List>
      {tabs.map((tab) => (
        <RadixTabs.Content key={tab.id} value={tab.id}>
          {tab.content}
        </RadixTabs.Content>
      ))}
    </RadixTabs.Root>
  );
}

type ToastMessage = { id: number; text: string; action?: { label: string; run: () => void } };
const ToastContext = createContext<(text: string, action?: ToastMessage["action"]) => void>(
  () => undefined,
);

/** Brief confirmations ("Check-in saved"). Announced politely, never the only signal. */
export function ToastProvider({ children, closeLabel }: { children: ReactNode; closeLabel: string }) {
  const [messages, setMessages] = useState<ToastMessage[]>([]);
  const show = useCallback((text: string, action?: ToastMessage["action"]) => {
    setMessages((current) => [...current.slice(-2), { id: Date.now() + Math.random(), text, action }]);
  }, []);
  const value = useMemo(() => show, [show]);
  return (
    <ToastContext.Provider value={value}>
      <RadixToast.Provider duration={6000} label={closeLabel}>
        {children}
        {messages.map((message) => (
          <RadixToast.Root
            key={message.id}
            onOpenChange={(open) =>
              !open && setMessages((current) => current.filter((m) => m.id !== message.id))
            }
            className="flex items-center gap-4 border border-line-strong bg-raised px-4 py-3"
          >
            <RadixToast.Description className="grow">{message.text}</RadixToast.Description>
            {message.action ? (
              <RadixToast.Action altText={message.action.label} asChild>
                <button type="button" className={buttonClass("quiet")} onClick={message.action.run}>
                  {message.action.label}
                </button>
              </RadixToast.Action>
            ) : null}
            <RadixToast.Close aria-label={closeLabel} className="h-11 w-11 text-dim">
              <span aria-hidden="true">×</span>
            </RadixToast.Close>
          </RadixToast.Root>
        ))}
        <RadixToast.Viewport className="fixed inset-x-4 bottom-24 z-50 mx-auto flex max-w-md flex-col gap-2 lg:bottom-6" />
      </RadixToast.Provider>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}

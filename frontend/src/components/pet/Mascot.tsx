"use client";

import { useEffect, useState } from "react";

import { CatFace, type Expression } from "@/components/pet/CatFace";
import { useReducedMotion } from "@/lib/prefs";

const CYCLE: readonly Expression[] = ["happy", "curious", "neutral", "happy", "surprised", "calm"];

/**
 * Sushi, the mascot, changing expression every few seconds. Holds one friendly face
 * for anyone who has turned motion off.
 */
export function MascotCycle({ label, className = "" }: { label?: string; className?: string }) {
  const still = useReducedMotion();
  const [step, setStep] = useState(0);
  useEffect(() => {
    if (still) return;
    const timer = window.setInterval(() => setStep((current) => current + 1), 3200);
    return () => window.clearInterval(timer);
  }, [still]);
  const expression = still ? "happy" : CYCLE[step % CYCLE.length]!;
  return <CatFace label={label} expression={expression} hop={expression === "happy" && step > 0} className={className} />;
}

/**
 * Sushi on the sign-in and create-account cards. Curious while you type, covers its
 * eyes while you type a password, happy otherwise. Purely decoration: it reads only
 * which kind of field has focus, never what is typed.
 */
export function FormMascot({ className = "" }: { className?: string }) {
  const [expression, setExpression] = useState<Expression>("happy");
  useEffect(() => {
    const onFocus = (event: FocusEvent) => {
      const field = event.target as HTMLElement | null;
      if (!(field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement)) return;
      setExpression(field.type === "password" ? "shy" : "curious");
    };
    const onBlur = () => setExpression("happy");
    document.addEventListener("focusin", onFocus);
    document.addEventListener("focusout", onBlur);
    return () => {
      document.removeEventListener("focusin", onFocus);
      document.removeEventListener("focusout", onBlur);
    };
  }, []);
  return <CatFace expression={expression} className={className} />;
}

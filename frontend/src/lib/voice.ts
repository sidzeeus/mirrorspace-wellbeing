"use client";

/**
 * Talking to the chat with your voice, using what the browser already has (free).
 *
 * - Listening uses the Web Speech API's speech recognition. In Chrome and Edge the
 *   browser sends the audio to its maker's speech service (Google or Microsoft) to turn
 *   it into text. This app never records, stores or sends audio itself: it only ever
 *   receives the text. Not available in Firefox.
 * - Speaking uses the device's own text-to-speech voices (speechSynthesis).
 *
 * The microphone is on only between a tap on "Talk" and the end of what was said.
 */
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";

type RecognitionResult = { isFinal: boolean; 0: { transcript: string } };
type RecognitionEvent = { resultIndex: number; results: ArrayLike<RecognitionResult> };
type RecognitionErrorEvent = { error: string };
type Recognition = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((event: RecognitionEvent) => void) | null;
  onerror: ((event: RecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};
type RecognitionConstructor = new () => Recognition;

function recognitionClass(): RecognitionConstructor | null {
  if (typeof window === "undefined") return null;
  const scope = window as unknown as {
    SpeechRecognition?: RecognitionConstructor;
    webkitSpeechRecognition?: RecognitionConstructor;
  };
  return scope.SpeechRecognition ?? scope.webkitSpeechRecognition ?? null;
}

const noop = () => () => undefined;
const useMounted = () =>
  useSyncExternalStore(
    noop,
    () => true,
    () => false,
  );

/** BCP 47 tag for the interface language: Indian English or Hindi. */
export const speechLang = (locale: string) => (locale === "hi" ? "hi-IN" : "en-IN");

export type ListenHandlers = {
  /** Words heard so far, updated while the person speaks. */
  onInterim: (text: string) => void;
  /** Everything said, once they stop. Empty if nothing was heard. */
  onFinal: (text: string) => void;
  onError: (code: "not-allowed" | "no-speech" | "network" | "other") => void;
};

export function useSpeechRecognition(lang: string) {
  const mounted = useMounted();
  const supported = mounted && recognitionClass() !== null;
  const [listening, setListening] = useState(false);
  const current = useRef<Recognition | null>(null);

  const stop = useCallback(() => current.current?.stop(), []);

  const start = useCallback(
    (handlers: ListenHandlers) => {
      const Constructor = recognitionClass();
      if (!Constructor || current.current) return;
      const recognition = new Constructor();
      recognition.lang = lang;
      recognition.interimResults = true;
      recognition.continuous = false;
      let finalText = "";
      recognition.onresult = (event) => {
        let interim = "";
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const result = event.results[i]!;
          if (result.isFinal) finalText += result[0].transcript;
          else interim += result[0].transcript;
        }
        handlers.onInterim((finalText + interim).trim());
      };
      recognition.onerror = (event) => {
        const code =
          event.error === "not-allowed" || event.error === "service-not-allowed"
            ? "not-allowed"
            : event.error === "no-speech"
              ? "no-speech"
              : event.error === "network"
                ? "network"
                : event.error === "aborted"
                  ? null
                  : "other";
        if (code) handlers.onError(code);
      };
      recognition.onend = () => {
        current.current = null;
        setListening(false);
        handlers.onFinal(finalText.trim());
      };
      current.current = recognition;
      setListening(true);
      recognition.start();
    },
    [lang],
  );

  // Never leave the microphone on when the screen goes away.
  useEffect(() => () => current.current?.abort(), []);

  return { supported, listening, start, stop };
}

/** Splits a reply into sentences, so long replies are not cut off and start sooner. */
function sentences(text: string): string[] {
  return (text.match(/[^.!?\n]+[.!?]*/g) ?? [text]).map((part) => part.trim()).filter(Boolean);
}

/*
  Mira's voice: soft and feminine. Devices offer different voices, so these are tried
  in order, natural-sounding ones first; the first one this device has is used.
*/
const PREFERRED_VOICES = [
  // Microsoft natural voices (Edge, Windows 11)
  "Neerja",
  "Swara",
  "Aria",
  "Jenny",
  "Ava",
  "Emma",
  "Sonia",
  "Libby",
  // Google voices (Chrome)
  "Google UK English Female",
  "Google US English",
  "Google हिन्दी",
  // Apple voices (Safari, iOS, macOS)
  "Samantha",
  "Veena",
  "Lekha",
  "Karen",
  "Moira",
  "Tessa",
  // Older Windows voices
  "Heera",
  "Kalpana",
  "Zira",
  "Hazel",
  "Susan",
];
const FEMALE_HINT = /female|woman|girl/i;

function pickVoice(voices: SpeechSynthesisVoice[], lang: string): SpeechSynthesisVoice | null {
  const base = lang.split("-")[0]!;
  const inLanguage = voices.filter((voice) => voice.lang.replace("_", "-").startsWith(base));
  for (const name of PREFERRED_VOICES) {
    const exact = inLanguage.find((voice) => voice.lang === lang && voice.name.includes(name));
    if (exact) return exact;
  }
  for (const name of PREFERRED_VOICES) {
    const found = inLanguage.find((voice) => voice.name.includes(name));
    if (found) return found;
  }
  return (
    inLanguage.find((voice) => FEMALE_HINT.test(voice.name)) ??
    inLanguage.find((voice) => voice.lang === lang) ??
    inLanguage[0] ??
    null
  );
}

export function useSpeechSynthesis(lang: string) {
  const mounted = useMounted();
  const supported = mounted && typeof window !== "undefined" && "speechSynthesis" in window;
  const [speaking, setSpeaking] = useState(false);

  const stop = useCallback(() => {
    if (!supported) return;
    window.speechSynthesis.cancel();
    setSpeaking(false);
  }, [supported]);

  const speak = useCallback(
    (text: string) => {
      if (!supported || !text.trim()) return;
      const synth = window.speechSynthesis;
      synth.cancel();
      const voice = pickVoice(synth.getVoices(), lang);
      const parts = sentences(text);
      parts.forEach((part, index) => {
        const utterance = new SpeechSynthesisUtterance(part);
        utterance.lang = voice?.lang ?? lang;
        if (voice) utterance.voice = voice;
        // Unhurried and soft: a touch slower, a touch higher, a little quieter.
        utterance.rate = 0.92;
        utterance.pitch = 1.08;
        utterance.volume = 0.9;
        if (index === 0) utterance.onstart = () => setSpeaking(true);
        if (index === parts.length - 1) {
          utterance.onend = () => setSpeaking(false);
          utterance.onerror = () => setSpeaking(false);
        }
        synth.speak(utterance);
      });
    },
    [lang, supported],
  );

  // Chrome fills the voice list a moment after load; asking once warms it up, so the
  // chosen voice is ready by the first reply.
  useEffect(() => {
    if (!supported) return;
    window.speechSynthesis.getVoices();
    const ready = () => window.speechSynthesis.getVoices();
    window.speechSynthesis.addEventListener?.("voiceschanged", ready);
    return () => window.speechSynthesis.removeEventListener?.("voiceschanged", ready);
  }, [supported]);

  // Stop talking when the person leaves the screen.
  useEffect(() => () => (supported ? window.speechSynthesis.cancel() : undefined), [supported]);

  return { supported, speaking, speak, stop };
}

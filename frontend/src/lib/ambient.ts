"use client";

/**
 * Soft piano music and calming sounds, made in the browser with the Web Audio API.
 * Nothing is downloaded, there is no licence to worry about, and no two minutes are
 * exactly the same.
 *
 * Programs:
 *   background  light piano in a major key, played sparsely, behind every page
 *   sleep       slower and lower, with soft rain
 *   relax       gentle piano with a warm pad underneath
 *   calm        a pad that swells for 4 seconds and settles for 6, with slow waves,
 *               to breathe along with
 *
 * Browsers only allow sound after the person has interacted with the page, so the
 * background music starts on the first tap, click or key press (AmbientMusic.tsx). It
 * drops to a whisper while the chat speaks or listens, and falls silent on Support.
 */

export type Program = "background" | "sleep" | "relax" | "calm";
type Listener = () => void;

// Chords as MIDI notes: C add9, A minor 7, F major 7, G suspended. Bright and settled.
const PROGRESSION = [
  [48, 55, 60, 62, 64, 67],
  [45, 52, 57, 60, 64, 67],
  [41, 48, 53, 57, 60, 64],
  [43, 50, 55, 57, 62, 67],
];
const MELODY = [72, 74, 76, 79, 81, 84]; // C major pentatonic, high and light

type Shape = {
  /** Seconds between notes. */
  step: number;
  /** Chance that a step plays a note at all: space is part of the calm. */
  density: number;
  /** Shift the whole thing up or down, in semitones. */
  transpose: number;
  /** Notes per chord before moving on. */
  perChord: number;
  melody: number;
  pad: number;
  noise: "none" | "rain" | "waves";
  volume: number;
};

const SHAPES: Record<Program, Shape> = {
  background: { step: 0.62, density: 0.72, transpose: 0, perChord: 8, melody: 0.12, pad: 0, noise: "none", volume: 0.3 },
  relax: { step: 0.78, density: 0.8, transpose: 0, perChord: 8, melody: 0.15, pad: 0.05, noise: "none", volume: 0.36 },
  sleep: { step: 1.35, density: 0.6, transpose: -5, perChord: 6, melody: 0.05, pad: 0.03, noise: "rain", volume: 0.32 },
  calm: { step: 1.0, density: 0.35, transpose: -2, perChord: 10, melody: 0, pad: 0.07, noise: "waves", volume: 0.36 },
};

const DUCKED = 0.25; // share of normal volume while the chat speaks or listens
const midi = (note: number) => 440 * 2 ** ((note - 69) / 12);

class Ambient {
  private context: AudioContext | null = null;
  private master: GainNode | null = null;
  private bus: AudioNode | null = null;
  private timer: number | null = null;
  private noise: { source: AudioBufferSourceNode; gain: GainNode } | null = null;
  private padTimer: number | null = null;
  private step = 0;
  private ducks = 0;
  private hushed = false;
  private userVolume = 1;
  program: Program = "background";
  playing = false;
  private listeners = new Set<Listener>();

  subscribe = (listener: Listener) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  snapshot = () => `${this.playing ? this.program : "off"}`;

  private notify() {
    this.listeners.forEach((listener) => listener());
  }

  private build(): boolean {
    if (this.context) return true;
    const Context =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Context) return false;
    const context = new Context();
    const master = context.createGain();
    master.gain.value = 0;
    const tone = context.createBiquadFilter();
    tone.type = "lowpass";
    tone.frequency.value = 3600;
    // A soft room: two quiet echoes at different distances.
    const echoA = context.createDelay(2);
    echoA.delayTime.value = 0.37;
    const echoB = context.createDelay(2);
    echoB.delayTime.value = 0.61;
    const feedback = context.createGain();
    feedback.gain.value = 0.3;
    const wet = context.createGain();
    wet.gain.value = 0.28;
    tone.connect(master);
    tone.connect(echoA);
    echoA.connect(echoB);
    echoB.connect(feedback);
    feedback.connect(echoA);
    echoA.connect(wet);
    echoB.connect(wet);
    wet.connect(master);
    master.connect(context.destination);
    this.context = context;
    this.master = master;
    this.bus = tone;
    return true;
  }

  private level(): number {
    if (this.hushed || !this.playing) return 0;
    const base = SHAPES[this.program].volume * this.userVolume;
    return this.ducks > 0 ? base * DUCKED : base;
  }

  private fadeTo(value: number, seconds: number) {
    if (!this.context || !this.master) return;
    const now = this.context.currentTime;
    this.master.gain.cancelScheduledValues(now);
    this.master.gain.setValueAtTime(this.master.gain.value, now);
    this.master.gain.linearRampToValueAtTime(value, now + seconds);
  }

  /** A soft piano-like note: a few harmonics, a quick touch, a long gentle fade. */
  private piano(note: number, when: number, velocity: number) {
    const context = this.context!;
    const frequency = midi(note);
    const decay = Math.max(1.6, 4.2 - (note - 48) * 0.06);
    const out = context.createGain();
    out.gain.setValueAtTime(0, when);
    out.gain.linearRampToValueAtTime(velocity, when + 0.012);
    out.gain.exponentialRampToValueAtTime(velocity * 0.35, when + 0.4);
    out.gain.exponentialRampToValueAtTime(0.0001, when + decay);
    out.connect(this.bus!);
    [
      [1, 1],
      [2, 0.32],
      [3, 0.1],
      [4, 0.05],
    ].forEach(([partial, amount]) => {
      const oscillator = context.createOscillator();
      oscillator.type = "sine";
      oscillator.frequency.value = frequency * partial!;
      oscillator.detune.value = (Math.random() - 0.5) * 4;
      const gain = context.createGain();
      gain.gain.value = amount!;
      oscillator.connect(gain);
      gain.connect(out);
      oscillator.start(when);
      oscillator.stop(when + decay + 0.05);
    });
  }

  /** A warm held chord underneath, swelling in and out. */
  private pad(notes: number[], when: number, length: number, level: number) {
    const context = this.context!;
    notes.slice(0, 4).forEach((note) => {
      const oscillator = context.createOscillator();
      oscillator.type = "triangle";
      oscillator.frequency.value = midi(note);
      const gain = context.createGain();
      gain.gain.setValueAtTime(0, when);
      gain.gain.linearRampToValueAtTime(level, when + length * 0.4);
      gain.gain.linearRampToValueAtTime(0, when + length);
      oscillator.connect(gain);
      gain.connect(this.bus!);
      oscillator.start(when);
      oscillator.stop(when + length + 0.05);
    });
  }

  private startNoise(kind: Shape["noise"]) {
    if (kind === "none" || !this.context) return;
    const context = this.context;
    const buffer = context.createBuffer(1, context.sampleRate * 4, context.sampleRate);
    const data = buffer.getChannelData(0);
    // Brown-ish noise: soft, without hiss.
    let last = 0;
    for (let i = 0; i < data.length; i += 1) {
      last = (last + 0.02 * (Math.random() * 2 - 1)) / 1.02;
      data[i] = last * 3.2;
    }
    const source = context.createBufferSource();
    source.buffer = buffer;
    source.loop = true;
    const filter = context.createBiquadFilter();
    filter.type = kind === "rain" ? "bandpass" : "lowpass";
    filter.frequency.value = kind === "rain" ? 1400 : 420;
    filter.Q.value = kind === "rain" ? 0.4 : 0.7;
    const gain = context.createGain();
    gain.gain.value = kind === "rain" ? 0.35 : 0.0;
    source.connect(filter);
    filter.connect(gain);
    gain.connect(this.master!);
    source.start();
    this.noise = { source, gain };
  }

  private stopNoise() {
    if (!this.noise || !this.context) return;
    const { source, gain } = this.noise;
    const now = this.context.currentTime;
    gain.gain.cancelScheduledValues(now);
    gain.gain.setValueAtTime(gain.gain.value, now);
    gain.gain.linearRampToValueAtTime(0, now + 1.5);
    source.stop(now + 1.6);
    this.noise = null;
  }

  private tick() {
    if (!this.context) return;
    const shape = SHAPES[this.program];
    const chord = PROGRESSION[Math.floor(this.step / shape.perChord) % PROGRESSION.length]!;
    const position = this.step % shape.perChord;
    const when = this.context.currentTime + 0.05;
    // Each chord begins with its low note, so the harmony is always clear.
    if (position === 0) {
      this.piano(chord[0]! + shape.transpose, when, 0.16);
      if (shape.pad > 0) this.pad(chord.map((n) => n + 12 + shape.transpose), when, shape.step * shape.perChord * 1.1, shape.pad);
    } else if (Math.random() < shape.density) {
      const note = chord[1 + Math.floor(Math.random() * (chord.length - 1))]! + 12 + shape.transpose;
      this.piano(note, when + Math.random() * 0.06, 0.07 + Math.random() * 0.05);
    }
    if (shape.melody > 0 && position % 2 === 1 && Math.random() < shape.melody) {
      const note = MELODY[Math.floor(Math.random() * MELODY.length)]! + shape.transpose;
      this.piano(note, when + shape.step / 2, 0.05);
    }
    this.step += 1;
  }

  /** Waves for "calm": in for 4 seconds, out for 6. */
  private breathe() {
    if (!this.noise || !this.context || this.program !== "calm") return;
    const now = this.context.currentTime;
    const gain = this.noise.gain.gain;
    gain.cancelScheduledValues(now);
    gain.setValueAtTime(gain.value, now);
    gain.linearRampToValueAtTime(0.55, now + 4);
    gain.linearRampToValueAtTime(0.08, now + 10);
  }

  /** Start a program (the background music by default). Must follow a tap or key press. */
  play(program: Program = "background") {
    if (!this.build() || !this.context) return;
    if (this.playing && this.program === program) return;
    this.stopLoops();
    this.program = program;
    this.step = 0;
    void this.context.resume();
    this.playing = true;
    const shape = SHAPES[program];
    this.tick();
    this.timer = window.setInterval(() => this.tick(), shape.step * 1000);
    this.startNoise(shape.noise);
    if (program === "calm") {
      this.breathe();
      this.padTimer = window.setInterval(() => this.breathe(), 10_000);
    }
    this.fadeTo(this.level(), 3);
    this.notify();
  }

  private stopLoops() {
    if (this.timer !== null) window.clearInterval(this.timer);
    if (this.padTimer !== null) window.clearInterval(this.padTimer);
    this.timer = null;
    this.padTimer = null;
    this.stopNoise();
  }

  pause() {
    if (!this.playing) return;
    this.playing = false;
    this.stopLoops();
    this.fadeTo(0, 1.5);
    const context = this.context;
    window.setTimeout(() => {
      if (!this.playing) void context?.suspend();
    }, 1700);
    this.notify();
  }

  /** 0 to 1, on top of each program's own level. */
  setVolume(value: number) {
    this.userVolume = Math.max(0, Math.min(1, value));
    if (this.playing) this.fadeTo(this.level(), 0.3);
  }

  /** Quieter while the chat speaks or listens. Calls nest: each `true` needs a `false`. */
  duck(on: boolean) {
    this.ducks = Math.max(0, this.ducks + (on ? 1 : -1));
    if (this.playing) this.fadeTo(this.level(), 0.6);
  }

  /** Silent on screens that must stay calm and clear (Support), without stopping. */
  hush(on: boolean) {
    this.hushed = on;
    if (this.playing) this.fadeTo(this.level(), on ? 1.5 : 3);
  }
}

export const ambient = new Ambient();

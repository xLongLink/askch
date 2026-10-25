"use client";

import * as React from "react";
import { Check, Loader2, Mic, Square, X } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";

import { cn } from "cn";

type VoiceState = "idle" | "listening" | "processing";

/**
 * Read microphone loudness from the existing recording stream without requesting a second microphone.
 */
function useMicrophoneLevel(stream: MediaStream | null) {
    const [level, setLevel] = React.useState(0);
    const [error, setError] = React.useState<string | null>(null);

    React.useEffect(() => {
        if (!stream) {
            setLevel(0);
            return;
        }
        let raf = 0;
        let ctx: AudioContext | undefined;

        function start(stream: MediaStream) {
            try {
                ctx = new AudioContext();
                const analyser = ctx.createAnalyser();
                analyser.fftSize = 256;
                ctx.createMediaStreamSource(stream).connect(analyser);
                const data = new Uint8Array(analyser.frequencyBinCount);
                const tick = () => {
                    analyser.getByteTimeDomainData(data);
                    let sum = 0;
                    for (const v of data) sum += ((v - 128) / 128) ** 2;
                    setLevel(Math.min(1, Math.sqrt(sum / data.length) * 3.2));
                    raf = requestAnimationFrame(tick);
                };
                tick();
            } catch (e) {
                setError(e instanceof Error ? e.message : "Microphone unavailable");
            }
        }
        setError(null);
        start(stream);

        return () => {
            cancelAnimationFrame(raf);
            void ctx?.close();
        };
    }, [stream]);

    return { level, error };
}

function formatClock(total: number) {
    const s = Math.max(0, Math.floor(total));
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

type VoiceInputProps = Omit<React.ComponentProps<"div">, "children" | "onChange"> & {
    /** Current state (controlled). Without it the component keeps its own state and moves idle → listening → processing. */
    state?: VoiceState;
    disabled?: boolean;
    /** Called when recording should begin. */
    onStart?: () => void;
    /** Called when the person finishes and wants the audio used. */
    onStop?: () => void;
    /** Called when the person throws the recording away. */
    onCancel?: () => void;
    /** Loudness from 0 to 1, for example from `useMicrophoneLevel`. Drives the waveform and the button's glow. */
    level?: number;
    /** "button" is a single round microphone button. "bar" expands into a recorder with waveform, timer, cancel and send. */
    variant?: "button" | "bar";
    /** Seconds recorded. When omitted the component times itself. */
    duration?: number;
    /** Text in the bar while processing. */
    processingLabel?: string;
    /** Accessible name of the button when idle. */
    label?: string;
};

const BAR_COUNT = 32;

function VoiceInput({
    state: stateProp,
    disabled = false,
    onStart,
    onStop,
    onCancel,
    level = 0,
    variant = "button",
    duration,
    processingLabel = "Transcribing…",
    label = "Start voice input",
    className,
    ...props
}: VoiceInputProps) {
    const reduce = useReducedMotion();
    const [internal, setInternal] = React.useState<VoiceState>("idle");
    const state = stateProp ?? internal;
    const [seconds, setSeconds] = React.useState(0);
    const [history, setHistory] = React.useState<number[]>(() => Array<number>(BAR_COUNT).fill(0));
    const startRef = React.useRef<HTMLButtonElement>(null);
    const prev = React.useRef<VoiceState>(state);

    const listening = state === "listening";

    React.useEffect(() => {
        if (!listening) {
            setSeconds(0);
            setHistory(Array<number>(BAR_COUNT).fill(0));
            return;
        }
        const id = setInterval(() => setSeconds((s) => s + 1), 1000);
        return () => clearInterval(id);
    }, [listening]);

    const levelRef = React.useRef(level);
    React.useEffect(() => {
        levelRef.current = level;
    });
    // Sample the level on a steady beat so the waveform scrolls even when the level holds still.
    React.useEffect(() => {
        if (!listening || variant !== "bar") return;
        const id = setInterval(() => {
            setHistory((h) => [...h.slice(1), Math.min(1, Math.max(0, levelRef.current))]);
        }, 70);
        return () => clearInterval(id);
    }, [listening, variant]);

    // After a recording ends, put focus back where the microphone button is.
    React.useEffect(() => {
        if (prev.current !== "idle" && state === "idle") startRef.current?.focus();
        prev.current = state;
    }, [state]);

    function start() {
        setInternal("listening");
        onStart?.();
    }
    function stop() {
        setInternal("processing");
        onStop?.();
    }
    function cancel() {
        setInternal("idle");
        onCancel?.();
    }

    const shownSeconds = duration ?? seconds;
    const announce = listening ? "Listening" : state === "processing" ? processingLabel : "";
    const escape = (e: React.KeyboardEvent) => {
        if (e.key === "Escape" && listening) {
            e.stopPropagation();
            cancel();
        }
    };

    if (variant === "button") {
        return (
            <div
                data-slot="voice-input"
                data-state={state}
                data-variant="button"
                className={cn(
                    "relative inline-flex size-10 items-center justify-center",
                    className,
                )}
                onKeyDown={escape}
                {...props}
            >
                {listening && !reduce && (
                    <motion.span
                        aria-hidden="true"
                        className="pointer-events-none absolute inset-0 rounded-full bg-foreground/15"
                        animate={{ scale: 1 + level * 0.7, opacity: 0.4 + level * 0.6 }}
                        transition={{ type: "spring", stiffness: 260, damping: 18 }}
                    />
                )}
                <button
                    ref={startRef}
                    type="button"
                    disabled={disabled || state === "processing"}
                    aria-label={
                        listening
                            ? "Stop and use recording"
                            : state === "processing"
                              ? processingLabel
                              : label
                    }
                    aria-pressed={listening}
                    onClick={listening ? stop : start}
                    className={cn(
                        "relative inline-flex size-10 items-center justify-center rounded-full border outline-none transition-[background-color,color,border-color,box-shadow] duration-150 focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-progress motion-reduce:transition-none",
                        listening
                            ? "border-transparent bg-primary text-primary-foreground"
                            : "bg-background text-foreground shadow-xs hover:bg-accent",
                    )}
                >
                    {state === "processing" ? (
                        <Loader2
                            aria-hidden="true"
                            className="size-4 animate-spin motion-reduce:animate-none"
                        />
                    ) : listening ? (
                        <Square aria-hidden="true" className="size-3.5 fill-current" />
                    ) : (
                        <Mic aria-hidden="true" className="size-4" />
                    )}
                </button>
                <span className="sr-only" role="status" aria-live="polite">
                    {announce}
                </span>
            </div>
        );
    }

    return (
        <div
            data-slot="voice-input"
            data-state={state}
            data-variant="bar"
            className={cn("w-full max-w-md", className)}
            onKeyDown={escape}
            {...props}
        >
            {state === "idle" ? (
                <button
                    ref={startRef}
                    type="button"
                    onClick={start}
                    disabled={disabled}
                    className="inline-flex h-10 items-center gap-2 rounded-full border bg-background px-4 text-sm font-medium shadow-xs outline-none transition-colors hover:bg-accent focus-visible:ring-[3px] focus-visible:ring-ring/50"
                >
                    <Mic aria-hidden="true" className="size-4" />
                    {label}
                </button>
            ) : (
                <div className="flex h-12 items-center gap-2 rounded-full border bg-card px-1.5 shadow-xs">
                    <button
                        type="button"
                        onClick={cancel}
                        disabled={disabled}
                        aria-label="Discard recording"
                        className="inline-flex size-9 shrink-0 items-center justify-center rounded-full text-muted-foreground outline-none transition-colors hover:bg-accent hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:opacity-50"
                    >
                        <X aria-hidden="true" className="size-4" />
                    </button>
                    {listening ? (
                        <>
                            <div
                                aria-hidden="true"
                                className="flex h-8 min-w-0 flex-1 items-center justify-between gap-[3px] overflow-hidden px-1"
                            >
                                {history.map((v, i) => (
                                    <span
                                        key={i}
                                        className="w-[3px] shrink-0 rounded-full bg-foreground"
                                        style={{
                                            height: `${Math.max(12, Math.round(12 + v * 88))}%`,
                                            opacity: 0.25 + (i / BAR_COUNT) * 0.75,
                                        }}
                                    />
                                ))}
                            </div>
                            <span className="w-10 shrink-0 text-end font-mono text-xs text-muted-foreground tabular-nums">
                                <span className="sr-only">Recording time </span>
                                {formatClock(shownSeconds)}
                            </span>
                            <button
                                type="button"
                                onClick={stop}
                                aria-label="Stop and use recording"
                                className="inline-flex size-9 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground outline-none transition-colors hover:bg-primary/90 focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                            >
                                <Check aria-hidden="true" className="size-4" />
                            </button>
                        </>
                    ) : (
                        <p className="flex min-w-0 flex-1 items-center justify-center gap-2 pe-10 text-sm text-muted-foreground">
                            <Loader2
                                aria-hidden="true"
                                className="size-4 animate-spin motion-reduce:animate-none"
                            />
                            {processingLabel}
                        </p>
                    )}
                </div>
            )}
            <span className="sr-only" role="status" aria-live="polite">
                {announce}
            </span>
        </div>
    );
}

export { VoiceInput, useMicrophoneLevel, formatClock, type VoiceInputProps, type VoiceState };

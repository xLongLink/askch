import { useEffect, useEffectEvent, useRef, useState } from "react";
import { z } from "zod/v4";
import { useMicrophoneLevel } from "@/components/ballmac/voice-input";

const transcriptSchema = z.string().trim().min(1).max(100000);
const recordingFormats = ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus"];

export function useDictation(onTranscript: (text: string) => void) {
    const [phase, setPhase] = useState<"idle" | "starting" | "recording" | "transcribing">("idle");
    const [error, setError] = useState("");
    const [recordingStream, setRecordingStream] = useState<MediaStream | null>(null);
    const { level } = useMicrophoneLevel(phase === "recording" ? recordingStream : null);
    const active = phase !== "idle";
    const recorder = useRef<MediaRecorder | null>(null);
    const receiveTranscript = useEffectEvent(onTranscript);
    const supported =
        typeof navigator.mediaDevices !== "undefined" && typeof MediaRecorder !== "undefined";

    // Keep recording, upload, timers and microphone access within one cancellable session.
    useEffect(() => {
        if (!active) return;
        const controller = new AbortController();
        let stream: MediaStream | undefined;
        let timer: ReturnType<typeof setTimeout> | undefined;
        let current: MediaRecorder | undefined;

        async function dictate() {
            try {
                setError("");
                const mimeType = recordingFormats.find((format) =>
                    MediaRecorder.isTypeSupported(format),
                );
                if (!mimeType)
                    throw new Error("This browser does not support a compatible recording format.");
                stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                if (controller.signal.aborted) {
                    stream.getTracks().forEach((track) => track.stop());
                    return;
                }
                const recording = new MediaRecorder(stream, {
                    mimeType,
                    audioBitsPerSecond: 64000,
                });
                current = recording;
                recorder.current = recording;
                setRecordingStream(stream);

                // Stop after one minute and reject oversized or interrupted recordings.
                const audio = await new Promise<Blob>((resolve, reject) => {
                    const chunks: Blob[] = [];
                    let size = 0;
                    recording.ondataavailable = (event) => {
                        size += event.data.size;
                        if (size > 10 * 1024 * 1024) {
                            reject(new Error("Recording must be smaller than 10 MB."));
                            return;
                        }
                        chunks.push(event.data);
                    };
                    recording.onerror = () =>
                        reject(new Error("Recording failed. Please try again."));
                    recording.onstop = () => resolve(new Blob(chunks, { type: mimeType }));
                    recording.start(1000);
                    timer = setTimeout(() => {
                        if (recording.state !== "inactive") recording.stop();
                    }, 60000);
                    setPhase("recording");
                });
                clearTimeout(timer);
                stream.getTracks().forEach((track) => track.stop());
                recorder.current = null;
                if (controller.signal.aborted) return;
                if (!audio.size) throw new Error("The recording is empty. Please try again.");

                // Append only validated text to the draft; never send a chat message automatically.
                setPhase("transcribing");
                const response = await fetch("/api/dictation", {
                    method: "POST",
                    headers: { "Content-Type": mimeType },
                    body: audio,
                    signal: controller.signal,
                });
                if (!response.ok)
                    throw new Error("Unable to transcribe the recording. Please try again.");
                const data: unknown = await response.json();
                const text = transcriptSchema.parse(data);
                if (!controller.signal.aborted) receiveTranscript(text);
            } catch (failure) {
                if (!controller.signal.aborted) {
                    setError(
                        failure instanceof DOMException && failure.name === "NotAllowedError"
                            ? "Microphone access was denied. Allow access in your browser and try again."
                            : failure instanceof z.ZodError
                              ? "No speech was recognized. Please try again."
                              : failure instanceof Error
                                ? failure.message
                                : "Dictation failed. Please try again.",
                    );
                }
            } finally {
                clearTimeout(timer);
                if (current?.state !== "inactive") current?.stop();
                stream?.getTracks().forEach((track) => track.stop());
                if (!controller.signal.aborted) {
                    setRecordingStream(null);
                    setPhase("idle");
                }
            }
        }
        void dictate();
        return () => {
            controller.abort();
            clearTimeout(timer);
            if (current?.state !== "inactive") current?.stop();
            stream?.getTracks().forEach((track) => track.stop());
            recorder.current = null;
        };
    }, [active]);

    return {
        active,
        phase,
        error,
        supported,
        level,
        start: () => {
            if (!active && supported) setPhase("starting");
        },
        stop: () => {
            if (recorder.current?.state === "recording") recorder.current.stop();
        },
        cancel: () => setPhase("idle"),
    };
}

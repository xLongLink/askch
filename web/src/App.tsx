import { useEffect, useMemo, useRef, useState } from "react";
import { DefaultChatTransport } from "ai";
import { useChat } from "@ai-sdk/react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ArrowUp, CircleAlert, Square } from "lucide-react";
import { z } from "zod/v4";
import { AssistantMessage } from "./Assistant";
import { useDictation } from "./dictation";
import { VoiceInput } from "@/components/ballmac/voice-input";

const samplesSchema = z.array(z.string().trim().min(1).max(2000)).length(4);

export function App() {
    // Fix the initial UI language for the lifetime of this conversation.
    const [language] = useState(() => {
        const languages = navigator.languages.length ? navigator.languages : [navigator.language];
        return (
            languages
                .map((locale) => locale.toLowerCase().split("-")[0])
                .map((language) => (language === "gsw" ? "de" : language))
                .find((language) => ["de", "fr", "it", "rm", "en"].includes(language)) ?? "en"
        );
    });
    const transport = useMemo(
        () =>
            new DefaultChatTransport({
                body: { context: { language } },
            }),
        [language],
    );

    // Keep the SDK conversation ID stable across turns and handle transient tool errors.
    const { messages, status, error, sendMessage, clearError, regenerate, stop } = useChat({
        transport,
        onData: ({ type }) => {
            if (type === "data-tool-error") console.error("[Chat] Tool call failed.");
        },
        onError: () => {
            console.error("[Chat] Request failed.");
        },
    });
    const [input, setInput] = useState("");
    const dictation = useDictation((text) => {
        setInput((draft) => (draft.trim() ? `${draft.trimEnd()} ${text}` : text));
    });
    const [samples, setSamples] = useState<string[]>([]);
    const messagesEnd = useRef<HTMLParagraphElement>(null);
    const busy = status === "submitted" || status === "streaming";

    // Load optional conversation starters and cancel the request when leaving the page.
    useEffect(() => {
        const controller = new AbortController();
        async function loadSamples() {
            try {
                const response = await fetch("/api/samples", { signal: controller.signal });
                if (!response.ok) throw new Error("Unable to load sample messages.");
                const data: unknown = await response.json();
                const samples = samplesSchema.parse(data);
                if (!controller.signal.aborted) setSamples(samples);
            } catch {
                if (!controller.signal.aborted)
                    console.error("[Chat] Unable to load sample messages.");
            }
        }
        void loadSamples();
        return () => controller.abort();
    }, []);

    // Synchronize the scroll position with streamed content and request status.
    useEffect(() => {
        messagesEnd.current?.scrollIntoView({ behavior: "instant", block: "end" });
    }, [messages, status]);

    async function send() {
        if (!input.trim() || busy || dictation.active) return;

        // Clear the draft before starting the SDK request.
        const text = input.trim();
        setInput("");
        clearError();
        await sendMessage({ text });
    }

    return (
        <section
            className="chat-page flex h-dvh flex-col bg-cover bg-center"
            data-has-messages={String(messages.length > 0)}
        >
            <main
                className={`flex min-h-0 flex-1 flex-col ${messages.length === 0 ? "justify-center" : "justify-start"}`}
            >
                {messages.length > 0 && (
                    <section className="flex-1 overflow-y-auto">
                        <section
                            className="conversation mx-auto flex w-full max-w-3xl shrink-0 flex-col gap-8 px-5 py-8"
                            role="log"
                            aria-label="Conversation"
                            aria-live="polite"
                        >
                            {messages.map((message) => {
                                const text = message.parts
                                    .filter((part) => part.type === "text")
                                    .map((part) => part.text)
                                    .join("");
                                if (message.role === "user") {
                                    return (
                                        <section className="flex justify-end" key={message.id}>
                                            <p className="max-w-[85%] rounded-2xl bg-muted px-4 py-3 whitespace-pre-wrap wrap-anywhere">
                                                {text}
                                            </p>
                                        </section>
                                    );
                                }
                                if (message.role === "assistant" && text) {
                                    return (
                                        <AssistantMessage
                                            key={message.id}
                                            content={text}
                                            isStreaming={
                                                status === "streaming" &&
                                                message.id === messages.at(-1)?.id
                                            }
                                            busy={busy || dictation.active}
                                            onSend={async (text) => {
                                                if (busy || dictation.active) return;
                                                clearError();
                                                await sendMessage({ text });
                                            }}
                                        />
                                    );
                                }
                                return null;
                            })}
                            {status === "submitted" && (
                                <p
                                    className="animate-pulse text-base text-muted-foreground"
                                    role="status"
                                >
                                    Thinking…
                                </p>
                            )}
                            <p ref={messagesEnd} aria-hidden="true" />
                        </section>
                    </section>
                )}

                <section className="mx-auto w-full max-w-3xl shrink-0 px-5 pt-3 pb-4">
                    {messages.length === 0 && (
                        <header className="greeting text-center">
                            <p className="mb-6 text-4xl" role="img" aria-label="Swiss flag">
                                🇨🇭
                            </p>
                            <h1 className="mb-8 font-medium tracking-tight">
                                Grüezi! Bonjour! Ciao! Allegra!
                            </h1>
                        </header>
                    )}
                    {error && (
                        <Alert variant="destructive" className="mb-3 bg-background">
                            <CircleAlert aria-hidden="true" />
                            <AlertTitle>Unable to get a response</AlertTitle>
                            <AlertDescription>
                                <p>{error.message}</p>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={async () => {
                                        clearError();
                                        await regenerate();
                                    }}
                                >
                                    Try again
                                </Button>
                            </AlertDescription>
                        </Alert>
                    )}
                    <form
                        className="flex items-end gap-2 rounded-2xl border border-input bg-background/95 p-2 shadow-sm transition-shadow focus-within:ring-2 focus-within:ring-ring/30"
                        onSubmit={async (event) => {
                            event.preventDefault();
                            await send();
                        }}
                    >
                        {!dictation.active && (
                            <Textarea
                                aria-label="Message"
                                placeholder="Message…"
                                value={input}
                                onChange={(event) => setInput(event.target.value)}
                                rows={1}
                                className="max-h-40 min-h-10 min-w-0 flex-1 resize-none border-0 bg-transparent shadow-none focus-visible:ring-0"
                                onKeyDown={async (event) => {
                                    if (
                                        event.key === "Enter" &&
                                        !event.shiftKey &&
                                        !event.nativeEvent.isComposing
                                    ) {
                                        event.preventDefault();
                                        await send();
                                    }
                                }}
                            />
                        )}
                        <VoiceInput
                            variant={dictation.active ? "bar" : "button"}
                            className={dictation.active ? "min-w-0 max-w-none flex-1" : "shrink-0"}
                            state={
                                dictation.phase === "recording"
                                    ? "listening"
                                    : dictation.active
                                      ? "processing"
                                      : "idle"
                            }
                            level={dictation.level}
                            label="Dictate message"
                            processingLabel={
                                dictation.phase === "starting"
                                    ? "Waiting for microphone access…"
                                    : "Transcribing…"
                            }
                            title={
                                dictation.supported
                                    ? "Dictate message"
                                    : "Dictation requires a supported browser and HTTPS or localhost"
                            }
                            disabled={busy || !dictation.supported}
                            onStart={dictation.start}
                            onStop={dictation.stop}
                            onCancel={dictation.cancel}
                        />
                        {!dictation.active &&
                            (busy ? (
                                <Button
                                    type="button"
                                    aria-label="Stop response"
                                    title="Stop response"
                                    variant="secondary"
                                    size="icon-lg"
                                    onClick={stop}
                                >
                                    <Square fill="currentColor" aria-hidden="true" />
                                </Button>
                            ) : (
                                <Button
                                    type="submit"
                                    aria-label="Send message"
                                    title="Send message"
                                    size="icon-lg"
                                    disabled={!input.trim() || dictation.active}
                                >
                                    <ArrowUp aria-hidden="true" />
                                </Button>
                            ))}
                    </form>
                    {(dictation.error ||
                        dictation.phase === "starting" ||
                        dictation.phase === "transcribing") && (
                        <p
                            className="mt-2 text-sm text-muted-foreground"
                            role={dictation.error ? "alert" : "status"}
                        >
                            {dictation.error ||
                                (dictation.phase === "starting"
                                    ? "Waiting for microphone access…"
                                    : dictation.phase === "transcribing"
                                      ? "Transcribing…"
                                      : "")}
                        </p>
                    )}
                    {messages.length === 0 && samples.length > 0 && (
                        <section
                            className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2"
                            aria-label="Sample messages"
                        >
                            {samples.map((sample) => (
                                <Button
                                    variant="outline"
                                    key={sample}
                                    className="h-auto min-w-0 justify-start bg-background/80 px-4 py-3 text-left whitespace-normal wrap-anywhere"
                                    disabled={busy || dictation.active}
                                    onClick={async () => {
                                        if (busy || dictation.active) return;
                                        setInput("");
                                        clearError();
                                        await sendMessage({ text: sample });
                                    }}
                                >
                                    {sample}
                                </Button>
                            ))}
                        </section>
                    )}
                </section>
            </main>
            <footer className="shrink-0 px-4 pb-4 text-center text-xs text-muted-foreground [&_a]:underline [&_a]:underline-offset-4">
                AI can make mistakes · <a href="https://github.com/xLongLink/askch">Open Source</a>{" "}
                · Created by <a href="https://www.linkedin.com/company/longlink">LongLink SAGL</a>
            </footer>
        </section>
    );
}

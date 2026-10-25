import { useEffect, useMemo, useRef, useState } from "react";
import { DefaultChatTransport } from "ai";
import { useChat } from "@ai-sdk/react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ArrowUp, CircleAlert, Square } from "lucide-react";
import { AssistantMessage } from "@/components/assistant";
import { useDictation } from "@/lib/dictation";
import { VoiceInput } from "@/components/ui/voice-input";

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
    const messagesEnd = useRef<HTMLParagraphElement>(null);
    const busy = status === "submitted" || status === "streaming";

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
            className={`relative isolate flex h-dvh flex-col bg-[url('/alpine.jpg')] bg-cover bg-center before:pointer-events-none before:absolute before:inset-0 before:-z-10 ${messages.length > 0 ? "before:bg-background/83" : "before:bg-background/60"}`}
        >
            <main
                className={`flex min-h-0 flex-1 flex-col ${messages.length === 0 ? "justify-center" : "justify-start"}`}
            >
                {messages.length > 0 && (
                    <section className="flex-1 overflow-y-auto">
                        <section
                            className="mx-auto flex w-full max-w-3xl shrink-0 flex-col gap-8 px-5 py-8 text-[0.9375rem] leading-7"
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
                        <header className="text-center">
                            <h1 className="mb-8 text-[clamp(1.875rem,5vw,2.25rem)] leading-[1.2] font-medium tracking-tight">
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
                </section>
            </main>
            <footer className="shrink-0 px-4 pb-4 text-center text-xs text-muted-foreground [&_a]:underline [&_a]:underline-offset-4">
                AI can make mistakes · <a href="https://github.com/xLongLink/askch">Open Source</a>{" "}
                · Created by <a href="https://www.linkedin.com/company/longlink">LongLink</a> in{" "}
                <span role="img" aria-label="Switzerland">
                    🇨🇭
                </span>
            </footer>
        </section>
    );
}

import { useEffect, useMemo, useRef, useState } from "react";
import { DefaultChatTransport } from "ai";
import { useChat } from "@ai-sdk/react";
import { Banner } from "@astryxdesign/core/Banner";
import { Button } from "@astryxdesign/core/Button";
import { IconButton } from "@astryxdesign/core/IconButton";
import { HStack } from "@astryxdesign/core/HStack";
import { Text } from "@astryxdesign/core/Text";
import { TextArea } from "@astryxdesign/core/TextArea";
import { VStack } from "@astryxdesign/core/VStack";
import { ArrowUp, CircleAlert, Square } from "lucide-react";
import { AssistantMessage } from "./Assistant";

const defaultGreeting = { languages: ["en"], lang: "en", text: "Hello! Welcome." };
const greetings = [
  { languages: ["de", "gsw"], lang: "de-CH", text: "Grüezi! Willkommen." },
  { languages: ["fr"], lang: "fr-CH", text: "Bonjour ! Bienvenue." },
  { languages: ["it"], lang: "it-CH", text: "Ciao! Benvenuti." },
  { languages: ["rm"], lang: "rm-CH", text: "Allegra! Bainvegni." },
  defaultGreeting,
];

export function App() {
  // Fix the initial UI language for the lifetime of this conversation.
  const [greeting] = useState(() => {
    const languages = navigator.languages.length ? navigator.languages : [navigator.language];
    return (
      languages
        .map((locale) =>
          greetings.find((candidate) =>
            candidate.languages.includes(locale.toLowerCase().split("-")[0]),
          ),
        )
        .find((candidate) => candidate !== undefined) ?? defaultGreeting
    );
  });
  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        body: { context: { language: greeting.lang.split("-")[0] } },
      }),
    [greeting],
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
  const messagesEnd = useRef<HTMLDivElement>(null);
  const busy = status === "submitted" || status === "streaming";

  // Synchronize the scroll position with streamed content and request status.
  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: "instant", block: "end" });
  }, [messages, status]);

  async function send() {
    if (!input.trim() || busy) return;

    // Clear the draft before starting the SDK request.
    const text = input.trim();
    setInput("");
    clearError();
    await sendMessage({ text });
  }

  return (
    <VStack
      className="chat-page h-dvh bg-cover bg-center"
      data-has-messages={String(messages.length > 0)}
    >
      <VStack
        as="main"
        className="min-h-0 flex-1"
        vAlign={messages.length === 0 ? "center" : "start"}
      >
        {messages.length > 0 && (
          <VStack className="flex-1 overflow-y-auto">
            <VStack
              className="conversation mx-auto w-full max-w-3xl shrink-0"
              gap={8}
              paddingInline={5}
              paddingBlock={8}
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
                    <HStack hAlign="end" key={message.id}>
                      <Text
                        type="inherit"
                        className="message-bubble rounded-2xl bg-muted px-4 py-3 whitespace-pre-wrap wrap-anywhere"
                      >
                        {text}
                      </Text>
                    </HStack>
                  );
                }
                if (message.role === "assistant" && text) {
                  return (
                    <AssistantMessage
                      key={message.id}
                      content={text}
                      isStreaming={status === "streaming" && message.id === messages.at(-1)?.id}
                      busy={busy}
                      onSend={async (text) => {
                        if (busy) return;
                        clearError();
                        await sendMessage({ text });
                      }}
                    />
                  );
                }
                return null;
              })}
              {status === "submitted" && (
                <Text as="p" type="inherit" className="text-base text-secondary" role="status">
                  Thinking…
                </Text>
              )}
              <VStack ref={messagesEnd} />
            </VStack>
          </VStack>
        )}

        <VStack
          className="mx-auto w-full max-w-3xl shrink-0"
          paddingInline={5}
          paddingBlockStart={3}
          paddingBlockEnd={4}
        >
          {messages.length === 0 && (
            <VStack className="greeting text-center">
              <Text
                type="inherit"
                display="block"
                justify="center"
                className="mb-6"
                role="img"
                aria-label="Swiss flag"
              >
                🇨🇭
              </Text>
              <h1 className="mb-8 font-medium tracking-tight" lang={greeting.lang}>
                {greeting.text}
              </h1>
            </VStack>
          )}
          {error && (
            <VStack className="mb-3" role="alert">
              <Banner
                status="error"
                title="Unable to get a response"
                description={error.message}
                icon={<CircleAlert size={20} aria-hidden="true" />}
                endContent={
                  <Button
                    label="Try again"
                    variant="ghost"
                    size="sm"
                    clickAction={async () => {
                      clearError();
                      await regenerate();
                    }}
                  />
                }
              />
            </VStack>
          )}
          <form
            className="flex items-end gap-2 rounded-lg border border-border bg-muted p-2 focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-secondary"
            onSubmit={async (event) => {
              event.preventDefault();
              await send();
            }}
          >
            <TextArea
              label="Message"
              isLabelHidden
              placeholder="Message…"
              value={input}
              onChange={setInput}
              rows={1}
              size="lg"
              containerClassName="min-w-0 flex-1"
              controlClassName="border-0 bg-transparent shadow-none outline-none [&_textarea]:max-h-40 [&_textarea]:field-sizing-content [&_textarea]:resize-none"
              onKeyDown={async (event) => {
                if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                  event.preventDefault();
                  await send();
                }
              }}
            />
            {busy ? (
              <IconButton
                label="Stop response"
                tooltip="Stop response"
                size="lg"
                icon={<Square size={16} fill="currentColor" aria-hidden="true" />}
                onClick={stop}
              />
            ) : (
              <IconButton
                type="submit"
                label="Send message"
                tooltip="Send message"
                variant="primary"
                size="lg"
                isDisabled={!input.trim()}
                icon={<ArrowUp size={20} aria-hidden="true" />}
              />
            )}
          </form>
        </VStack>
      </VStack>
      <footer className="shrink-0 px-4 pb-4 text-center text-sm text-secondary [&_a]:underline">
        AI can make mistakes · <a href="https://github.com/xLongLink/askch">Open Source</a> ·
        Created by <a href="https://www.linkedin.com/company/longlink">LongLink SAGL</a>
      </footer>
    </VStack>
  );
}

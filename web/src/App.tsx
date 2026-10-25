import { useEffect, useMemo, useRef, useState } from "react";
import { DefaultChatTransport } from "ai";
import { useChat } from "@ai-sdk/react";
import { Banner } from "@astryxdesign/core/Banner";
import { Button } from "@astryxdesign/core/Button";
import { IconButton } from "@astryxdesign/core/IconButton";
import { TextArea } from "@astryxdesign/core/TextArea";
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
    <div className="chat-page" data-has-messages={messages.length > 0}>
      <main className={messages.length === 0 ? "chat-main is-empty" : "chat-main"}>
        {messages.length > 0 && (
          <div className="conversation-scroll">
            <div className="conversation" role="log" aria-label="Conversation" aria-live="polite">
              {messages.map((message) => {
                const text = message.parts
                  .filter((part) => part.type === "text")
                  .map((part) => part.text)
                  .join("");
                if (message.role === "user") {
                  return (
                    <div className="user-message" key={message.id}>
                      <div className="message-bubble">{text}</div>
                    </div>
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
                <p className="thinking" role="status">
                  Thinking…
                </p>
              )}
              <div ref={messagesEnd} />
            </div>
          </div>
        )}

        <div className="composer-section">
          {messages.length === 0 && (
            <div className="greeting">
              <span role="img" aria-label="Swiss flag">
                🇨🇭
              </span>
              <h1 lang={greeting.lang}>{greeting.text}</h1>
            </div>
          )}
          {error && (
            <div className="chat-error" role="alert">
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
            </div>
          )}
          <form
            className="composer"
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
              containerClassName="composer-input"
              controlClassName="composer-control"
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
        </div>
      </main>
      <footer className="chat-footer">
        AI can make mistakes · <a href="https://github.com/xLongLink/askch">Open Source</a> ·
        Created by <a href="https://www.linkedin.com/company/longlink">LongLink SAGL</a>
      </footer>
    </div>
  );
}

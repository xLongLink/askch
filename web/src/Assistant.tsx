import { useState } from "react";
import { Renderer } from "@openuidev/react-lang";
import { marked, type Token } from "marked";
import sanitizeHtml from "sanitize-html";
import { z } from "zod/v4";
import { library } from "./openui";

const followUpEvent = z.object({
    type: z.literal("continue_conversation"),
    humanFriendlyMessage: z.string().trim().min(1).max(2000),
});

function OpenUIBlock({
    code,
    isStreaming,
    busy,
    onSend,
}: {
    code: string;
    isStreaming: boolean;
    busy: boolean;
    onSend: (text: string) => Promise<void>;
}) {
    const [invalid, setInvalid] = useState(false);

    // Bound parsing work and keep oversized generated output visible as escaped text.
    if (code.length > 20000) return <pre className="max-h-80 overflow-x-auto">{code}</pre>;

    return (
        <section>
            <Renderer
                library={library}
                response={code}
                isStreaming={isStreaming}
                publishObservability={false}
                onError={(errors) =>
                    setInvalid(errors.some((error) => error.severity !== "warning"))
                }
                onAction={async (event) => {
                    // Generated buttons may only send a bounded, explicit user follow-up.
                    const result = followUpEvent.safeParse(event);
                    if (!result.success || busy || isStreaming) return;
                    await onSend(result.data.humanFriendlyMessage);
                }}
            />
            {invalid && !isStreaming && (
                <details>
                    <summary>
                        Some generated UI could not be displayed. View the original response.
                    </summary>
                    <pre className="max-h-80 overflow-x-auto">{code}</pre>
                </details>
            )}
        </section>
    );
}

export function AssistantMessage({
    content,
    isStreaming,
    busy,
    onSend,
}: {
    content: string;
    isStreaming: boolean;
    busy: boolean;
    onSend: (text: string) => Promise<void>;
}) {
    // Only explicitly labeled UI fences are interpreted; ordinary Markdown stays Markdown.
    const parts: Array<{ type: "markdown"; tokens: Token[] } | { type: "openui"; code: string }> =
        [];
    for (const token of marked.lexer(content)) {
        if (token.type === "code" && /^(openui-lang|openui)$/i.test(token.lang ?? "")) {
            parts.push({ type: "openui", code: token.text });
        } else {
            const previous = parts.at(-1);
            if (previous?.type === "markdown") previous.tokens.push(token);
            else parts.push({ type: "markdown", tokens: [token] });
        }
    }

    return (
        <article className="min-w-0 wrap-anywhere [&>*+*]:mt-4">
            {parts.map((part, index) =>
                part.type === "openui" ? (
                    <OpenUIBlock
                        key={index}
                        code={part.code}
                        isStreaming={isStreaming}
                        busy={busy}
                        onSend={onSend}
                    />
                ) : (
                    <section
                        key={index}
                        className="markdown min-w-0 wrap-anywhere [&>*+*]:mt-4"
                        dangerouslySetInnerHTML={{
                            __html: sanitizeHtml(marked.parser(part.tokens)),
                        }}
                    />
                ),
            )}
        </article>
    );
}

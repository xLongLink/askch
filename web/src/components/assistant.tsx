import { useState } from "react";
import { Renderer } from "@openuidev/react-lang";
import { marked, type Token } from "marked";
import sanitizeHtml from "sanitize-html";
import { componentArguments, library } from "@/lib/openui";
import { normalizeOpenUI } from "@/lib/normalize";

function OpenUIBlock({ code, isStreaming }: { code: string; isStreaming: boolean }) {
    const [invalid, setInvalid] = useState(false);

    // Bound parsing work and keep oversized generated output visible as escaped text.
    if (code.length > 20000) return <pre className="max-h-80 overflow-x-auto">{code}</pre>;

    return (
        <section>
            <Renderer
                library={library}
                response={normalizeOpenUI(code, componentArguments)}
                isStreaming={isStreaming}
                publishObservability={false}
                onError={(errors) =>
                    setInvalid(errors.some((error) => error.severity !== "warning"))
                }
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
}: {
    content: string;
    isStreaming: boolean;
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
                    <OpenUIBlock key={index} code={part.code} isStreaming={isStreaming} />
                ) : (
                    <section
                        key={index}
                        className="min-w-0 wrap-anywhere [&>*+*]:mt-4 [&_:is(h1,h2,h3,h4,h5,h6)]:mt-6 [&_:is(h1,h2,h3,h4,h5,h6)]:leading-[1.3] [&_:is(h1,h2,h3,h4,h5,h6)]:font-semibold [&_h1]:text-2xl [&_h2]:text-xl [&_h3]:text-lg [&_:is(ul,ol)]:pl-6 [&_ul]:list-disc [&_ol]:list-decimal [&_li+li]:mt-1 [&_li>:is(ul,ol)]:mt-1 [&_a]:underline [&_a]:underline-offset-[0.15em] [&_blockquote]:border-l-[3px] [&_blockquote]:pl-4 [&_blockquote]:text-muted-foreground [&_code]:rounded [&_code]:bg-muted [&_code]:px-[0.3em] [&_code]:py-[0.15em] [&_code]:text-[0.875em] [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:bg-muted [&_pre]:p-4 [&_pre_code]:p-0 [&_table]:block [&_table]:border-collapse [&_table]:overflow-x-auto [&_:is(th,td)]:border [&_:is(th,td)]:px-3 [&_:is(th,td)]:py-2 [&_:is(th,td)]:text-left [&_hr]:border-t"
                        dangerouslySetInnerHTML={{
                            __html: sanitizeHtml(marked.parser(part.tokens)),
                        }}
                    />
                ),
            )}
        </article>
    );
}

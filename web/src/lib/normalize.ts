/** Accept signature-style labels only in their declared positions, without changing values. */
export function normalizeOpenUI(
    code: string,
    componentArguments: ReadonlyMap<string, string[]>,
): string {
    const tokens =
        code.match(
            /"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\/\/[^\n]*|\/\*[\s\S]*?\*\/|[A-Za-z_$][\w$]*|\s+|./gs,
        ) ?? [];
    const frames: { delimiter: string; parameters?: string[]; argument: number; start: boolean }[] =
        [];
    const output: string[] = [];
    let previous = "";

    // Track calls separately from address objects, arrays, strings, and comments.
    for (let index = 0; index < tokens.length; index++) {
        const token = tokens[index];
        const frame = frames.at(-1);
        if (/^\s+$/.test(token)) {
            output.push(frames.length ? token.replace(/[\r\n]+/g, " ") : token);
            continue;
        }
        if (token.startsWith("//") || token.startsWith("/*")) return code;
        if (token === '"' || token === "'") return code;
        if (token === ":" && frame?.parameters) return code;

        // Remove a label only when it exactly matches this argument's schema key.
        if (frame?.parameters && frame.start && /^[A-Za-z_$][\w$]*$/.test(token)) {
            let next = index + 1;
            while (next < tokens.length && /^\s+$/.test(tokens[next])) next++;
            if (tokens[next] === ":") {
                if (token !== frame.parameters[frame.argument]) return code;
                frame.start = false;
                index = next;
                continue;
            }
        }

        // Preserve unknown or mismatched syntax for the renderer's normal error handling.
        if (token === "(" || token === "[" || token === "{") {
            if (frame) frame.start = false;
            frames.push({
                delimiter: token,
                parameters: token === "(" ? componentArguments.get(previous) : undefined,
                argument: 0,
                start: true,
            });
        } else if (token === ")" || token === "]" || token === "}") {
            const expected = token === ")" ? "(" : token === "]" ? "[" : "{";
            if (frame?.delimiter !== expected) return code;
            frames.pop();
        } else if (frame && token === ",") {
            frame.argument++;
            frame.start = true;
        } else if (frame) {
            frame.start = false;
        }
        output.push(token);
        previous = token;
    }
    return output.join("");
}

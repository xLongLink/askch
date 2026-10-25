import type { ComponentRenderProps } from "@openuidev/react-lang";
import { z } from "zod/v4";

export function AIGrid({ props, renderNode }: ComponentRenderProps) {
    const children = z
        .array(
            z.object({
                type: z.literal("element"),
                typeName: z.literal("Card"),
                props: z.record(z.string(), z.unknown()),
            }),
        )
        .max(20)
        .parse(props.children);
    return <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">{renderNode(children)}</div>;
}

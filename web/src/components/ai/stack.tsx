import type { ComponentRenderProps } from "@openuidev/react-lang";
import { z } from "zod/v4";

const stackChildrenSchema = z
    .array(
        z.object({
            type: z.literal("element"),
            typeName: z.enum([
                "Text",
                "Heading",
                "Link",
                "Chart",
                "Map",
                "Invoice",
                "Card",
                "Grid",
            ]),
            props: z.record(z.string(), z.unknown()),
        }),
    )
    .max(24);

export function AIStack({ props, renderNode }: ComponentRenderProps) {
    const children = stackChildrenSchema.parse(props.children);
    return <section className="space-y-4">{renderNode(children)}</section>;
}

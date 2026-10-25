import type { ComponentRenderProps } from "@openuidev/react-lang";
import { Card, CardContent } from "@/components/ui/card";
import { z } from "zod/v4";

// Validate evaluated children as element nodes, not the prompt's component-reference schemas.
const childrenSchema = z
    .array(
        z.object({
            type: z.literal("element"),
            typeName: z.enum(["Text", "Heading", "Link", "Chart", "Map", "Invoice"]),
            props: z.record(z.string(), z.unknown()),
        }),
    )
    .max(24);

export function AICard({ props, renderNode }: ComponentRenderProps) {
    const children = childrenSchema.parse(props.children);
    return (
        <Card>
            <CardContent className="space-y-4">{renderNode(children)}</CardContent>
        </Card>
    );
}

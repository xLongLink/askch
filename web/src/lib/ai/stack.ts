import { defineComponent } from "@openuidev/react-lang";
import { AIStack } from "@/components/ai/stack";
import { z } from "zod/v4";
import { card } from "./card";
import { chart } from "./chart";
import { grid } from "./grid";
import { heading } from "./heading";
import { invoice } from "./invoice";
import { link } from "./link";
import { map } from "./map";
import { text } from "./text";

export const stack = defineComponent({
    name: "Stack",
    description:
        "The root vertical layout, containing at most 24 basic components, cards, or grids. Do not nest stacks.",
    props: z.object({
        children: z
            .array(
                z.union([
                    text.ref,
                    heading.ref,
                    link.ref,
                    chart.ref,
                    map.ref,
                    invoice.ref,
                    card.ref,
                    grid.ref,
                ]),
            )
            .max(24),
    }),
    component: AIStack,
});

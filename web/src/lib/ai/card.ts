import { defineComponent } from "@openuidev/react-lang";
import { AICard } from "@/components/ai/card";
import { z } from "zod/v4";
import { chart } from "./chart";
import { heading } from "./heading";
import { invoice } from "./invoice";
import { link } from "./link";
import { map } from "./map";
import { text } from "./text";

export const card = defineComponent({
    name: "Card",
    description:
        "A card for a discrete item, containing at most 24 basic components. Do not nest cards or stacks.",
    props: z.object({
        children: z
            .array(z.union([text.ref, heading.ref, link.ref, chart.ref, map.ref, invoice.ref]))
            .max(24),
    }),
    component: AICard,
});

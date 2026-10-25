import { defineComponent } from "@openuidev/react-lang";
import { AIGrid } from "@/components/ai/grid";
import { z } from "zod/v4";
import { card } from "./card";

export const grid = defineComponent({
    name: "Grid",
    description:
        "A responsive grid of up to 20 cards, one per result. One column on narrow screens and two on wider screens.",
    props: z.object({ children: z.array(card.ref).max(20) }),
    component: AIGrid,
});

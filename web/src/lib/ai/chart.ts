import { defineComponent } from "@openuidev/react-lang";
import { AIChart, chartProps } from "@/components/ai/chart";

export const chart = defineComponent({
    name: "Chart",
    description:
        "A line or bar chart of real data. Include axis labels and units. Supply 1–100 labels and an array of 1–4 named series (a single series object is also accepted). Use null for missing data; omitted trailing values appear as gaps.",
    props: chartProps,
    component: AIChart,
});

import { createLibrary, defineComponent } from "@openuidev/svelte-lang";
import { z } from "zod";
import Stack from "./openui/Stack.svelte";
import Card from "./openui/Card.svelte";
import TextContent from "./openui/TextContent.svelte";
import Button from "./openui/Button.svelte";
import Chart from "./openui/Chart.svelte";

const text = defineComponent({
  name: "TextContent",
  props: z.object({ text: z.string() }),
  description: "Plain text paragraph. Use newlines for lists. Do not use Markdown or HTML.",
  component: TextContent,
});
const button = defineComponent({
  name: "Button",
  props: z.object({ label: z.string() }),
  description: "Suggested follow-up question; clicking sends the label as a message.",
  component: Button,
});
const chart = defineComponent({
  name: "Chart",
  props: z.object({
    title: z.string(),
    type: z.enum(["bar", "line", "pie", "doughnut"]),
    labels: z.array(z.string()),
    values: z.array(z.number()),
    datasetLabel: z.string().optional(),
  }),
  description:
    "Data visualization: bar for comparisons, line for trends, pie or doughnut for proportions. Labels and values must have the same length.",
  component: Chart,
});
const card = defineComponent({
  name: "Card",
  props: z.object({
    title: z.string(),
    children: z.array(z.union([text.ref, button.ref, chart.ref])),
  }),
  description: "Group related content in an optional titled card.",
  component: Card,
});
const stack = defineComponent({
  name: "Stack",
  props: z.object({ children: z.array(z.union([text.ref, button.ref, chart.ref, card.ref])) }),
  description: "Vertical layout. Always use this as the root.",
  component: Stack,
});

export const library = createLibrary({
  components: [text, button, chart, card, stack],
  root: "Stack",
});

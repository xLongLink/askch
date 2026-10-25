import {
    createLibrary,
    defineComponent,
    useIsStreaming,
    useTriggerAction,
    type PromptOptions,
} from "@openuidev/react-lang";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { z } from "zod/v4";
import { chart } from "./Chart";
import { map } from "./Map";

const textProps = z.object({ text: z.string().max(10000) });
const headingProps = z.object({
    text: z.string().min(1).max(200),
    level: z.union([z.literal(2), z.literal(3), z.literal(4)]).default(2),
});
const linkProps = z.object({
    label: z.string().min(1).max(200),
    url: z
        .url({ protocol: /^https?$/ })
        .max(2048)
        .refine((value) => {
            if (!URL.canParse(value)) return false;
            const url = new URL(value);
            return !url.username && !url.password;
        }, "Links must not contain credentials."),
});
const followUpProps = z.object({
    label: z.string().min(1).max(120),
    message: z.string().trim().min(1).max(2000),
});

const text = defineComponent({
    name: "Text",
    description: "A plain-text paragraph. No HTML or Markdown.",
    props: textProps,
    component: ({ props }) => {
        const data = textProps.parse(props);
        return <p className="leading-relaxed">{data.text}</p>;
    },
});

const heading = defineComponent({
    name: "Heading",
    description: "A section heading; level is 2, 3, or 4.",
    props: headingProps,
    component: ({ props }) => {
        const data = headingProps.parse(props);
        const Heading = `h${data.level}` as "h2" | "h3" | "h4";
        return (
            <Heading
                className={
                    data.level === 2
                        ? "text-xl font-semibold tracking-tight"
                        : "text-base font-semibold"
                }
            >
                {data.text}
            </Heading>
        );
    },
});

const link = defineComponent({
    name: "Link",
    description: "A descriptive link to an HTTP(S) source, without credentials.",
    props: linkProps,
    component: ({ props }) => {
        const data = linkProps.parse(props);
        return (
            <a
                className="text-primary underline underline-offset-4 hover:text-primary/80"
                href={data.url}
                target="_blank"
                rel="noopener noreferrer"
            >
                {data.label}
            </a>
        );
    },
});

const followUp = defineComponent({
    name: "FollowUp",
    description:
        "An optional button that sends its message as a user follow-up when clicked. No other actions.",
    props: followUpProps,
    component: ({ props }) => {
        const triggerAction = useTriggerAction();
        const isStreaming = useIsStreaming();
        const data = followUpProps.parse(props);
        return (
            <Button
                variant="outline"
                className="h-auto max-w-full justify-start whitespace-normal text-left"
                disabled={isStreaming}
                onClick={() => triggerAction(data.message)}
            >
                {data.label}
            </Button>
        );
    },
});

// Validate evaluated children as element nodes, not the prompt's component-reference schemas.
const childrenSchema = z
    .array(
        z.object({
            type: z.literal("element"),
            typeName: z.enum(["Text", "Heading", "Link", "FollowUp", "Chart", "Map"]),
            props: z.record(z.string(), z.unknown()),
        }),
    )
    .max(24);

const card = defineComponent({
    name: "Card",
    description:
        "A card for a discrete item, containing at most 24 basic components. Do not nest cards or stacks.",
    props: z.object({
        children: z
            .array(z.union([text.ref, heading.ref, link.ref, followUp.ref, chart.ref, map.ref]))
            .max(24),
    }),
    component: ({ props, renderNode }) => {
        const children = childrenSchema.parse(props.children);
        return (
            <Card>
                <CardContent className="space-y-4">{renderNode(children)}</CardContent>
            </Card>
        );
    },
});

const stackChildrenSchema = z
    .array(
        childrenSchema.element.extend({
            typeName: z.enum(["Text", "Heading", "Link", "FollowUp", "Chart", "Map", "Card"]),
        }),
    )
    .max(24);

const stack = defineComponent({
    name: "Stack",
    description:
        "The root vertical layout, containing at most 24 basic components or cards. Do not nest stacks.",
    props: z.object({
        children: z
            .array(
                z.union([
                    text.ref,
                    heading.ref,
                    link.ref,
                    followUp.ref,
                    chart.ref,
                    map.ref,
                    card.ref,
                ]),
            )
            .max(24),
    }),
    component: ({ props, renderNode }) => {
        const children = stackChildrenSchema.parse(props.children);
        return <section className="space-y-4">{renderNode(children)}</section>;
    },
});

// Keep the renderer and generated model instructions on the same component contract.
export const library = createLibrary({
    root: "Stack",
    components: [stack, card, heading, text, link, followUp, chart, map],
});
export const promptOptions: PromptOptions = {
    preamble:
        'You may answer in ordinary Markdown or include an interactive interface using the approved OpenUI components. UI programs must be inside openui-lang code fences; text outside them remains Markdown. Never return bare OpenUI code. Component calls use positional arguments, never named arguments: write Map("Title", "", [], [...]), not Map(title: "Title", unit: "", cantons: [], markers: [...]).',
    inlineMode: true,
    toolCalls: false,
    bindings: false,
    builtinFunctions: false,
    additionalRules: [
        "Prefer ordinary Markdown for simple conversational answers. Use UI only when it improves presentation or offers useful follow-ups.",
        "Wrap every UI program in a fenced openui-lang code block, with Markdown allowed before and after it.",
        "Every block is independent and must include a complete root = Stack([...]) statement. Never emit patches or rely on previous blocks.",
        'Component signatures describe argument order, not literal syntax. Never put property names or colons in component argument lists. Map arguments are title, unit, cantons, markers in that order. Chart arguments are title, type, xLabel, yLabel, labels, series in that order. Object fields inside arrays DO use colons, for example {label: "Bern", longitude: 7.4474, latitude: 46.948}. Keep each complete assignment on one line. Put explanations and notes outside the openui-lang fence, never inside the program.',
        "Only Stack, Card, Heading, Text, Link, FollowUp, Chart, and Map are available. Stack contains at most 24 basic components or cards, never another Stack.",
        "Use Card only for discrete, self-contained items, not every section. Each Card contains at most 24 Heading, Text, Link, FollowUp, Chart, or Map components. Never nest cards or stacks inside a Card.",
        "Use Map for Swiss locations or canton comparisons using real tool results or user-supplied data only. Never invent coordinates or values. Provide a title, unit (empty for locations only), cantons, and markers; pass [] for unused layers. Canton codes must be unique official two-letter abbreviations. Null and omitted canton values are neutral gray, not zero. All canton values must share the same unit. Marker coordinates are WGS84 longitude/latitude inside Switzerland's bounding box. Localize labels and cite data sources with Link. The bundled canton boundaries are generalized historical outlines from 2016: do not use them to assert current administrative borders or for navigation.",
        'Use Chart for trends (line) or comparisons (bar), using only data returned by tools or supplied by the user. Never invent chart values. Include units in axis labels and cite tool sources with Link when available. Pass series as an array even for one series: [{name: "Temperature", values: [12, null]}]. All series share the same unit. Copy labels and values from the same source rows so they stay aligned; do not invent a full day of hour labels for a shorter forecast. Use null for missing values, not zero. Before emitting a chart, check that each series has one value per label. Limit charts to 100 labels and 4 series. Localize titles, labels, and series names to the conversation language.',
        "Use plain strings in Text and Heading. Link URLs must be HTTP(S), with no embedded credentials. Cite actual official sources, not invented URLs.",
        "FollowUp only suggests a message for the user to send. It cannot execute tools or perform other actions. Keep messages below 2000 characters.",
        "Do not use Query, Mutation, actions, reactive variables, functions, HTML, or executable code. Fetch real data using the agent's existing MCP tools before writing the response.",
    ],
    examples: [
        'Here is an overview:\n\n```openui-lang\nroot = Stack([Card([Heading("Swiss information", 2), Text("Explore information from official Swiss sources."), Link("Swiss federal portal", "https://www.admin.ch/")]), FollowUp("Latest announcements", "Show me the latest official federal announcements")])\n```',
        'Map of user-supplied city coordinates:\n\n```openui-lang\nroot = Stack([Map("Switzerland – Key Cities", "", [], [{label: "Bern", longitude: 7.4474, latitude: 46.948}, {label: "Zürich", longitude: 8.5417, latitude: 47.3769}, {label: "Geneva", longitude: 6.1432, latitude: 46.2044}])])\n```\n\nThe map uses generalized historical canton boundaries, not current administrative or navigation data.',
        'Comparison of illustrative values supplied by the user, not real statistics:\n\n```openui-lang\nroot = Stack([Chart("Illustrative canton values", "bar", "Canton", "%", ["Zürich", "Bern"], [{name: "Illustrative values", values: [80, 60]}])])\n```',
    ],
};

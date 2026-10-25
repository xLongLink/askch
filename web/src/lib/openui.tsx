import { createLibrary, type PromptOptions } from "@openuidev/react-lang";
import { card } from "@/lib/ai/card";
import { chart } from "@/lib/ai/chart";
import { grid } from "@/lib/ai/grid";
import { heading } from "@/lib/ai/heading";
import { invoice } from "@/lib/ai/invoice";
import { link } from "@/lib/ai/link";
import { map } from "@/lib/ai/map";
import { stack } from "@/lib/ai/stack";
import { text } from "@/lib/ai/text";

// Keep the renderer and generated model instructions on the same component contract.
const components = [stack, card, grid, heading, text, link, chart, map, invoice];
export const componentArguments = new Map(
    components.map((component) => [component.name, Object.keys(component.props.shape)]),
);
export const library = createLibrary({
    root: "Stack",
    components,
});
export const promptOptions: PromptOptions = {
    preamble:
        'You may answer in ordinary Markdown or include an interactive interface using the approved OpenUI components. UI programs must be inside openui-lang code fences; text outside them remains Markdown. Never return bare OpenUI code. Component calls use positional arguments, never named arguments: write Map("Title", "", [], [...]), not Map(title: "Title", unit: "", cantons: [], markers: [...]).',
    inlineMode: true,
    toolCalls: false,
    bindings: false,
    builtinFunctions: false,
    additionalRules: [
        "Prefer ordinary Markdown for simple conversational answers. Use UI only when it improves presentation.",
        "Wrap every UI program in a fenced openui-lang code block, with Markdown allowed before and after it.",
        "Every block is independent and must include a complete root = Stack([...]) statement. Never emit patches or rely on previous blocks.",
        'Component signatures describe argument order, not literal syntax. Never put property names or colons in component argument lists. Map arguments are title, unit, cantons, markers in that order. Chart arguments are title, type, xLabel, yLabel, labels, series in that order. Invoice arguments are title, amount, currency, creditor, debtor, reference, message, language in that order. Object fields inside address objects and arrays DO use colons, for example {label: "Bern", longitude: 7.4474, latitude: 46.948}. Keep each complete assignment on one line. Put explanations and notes outside the openui-lang fence, never inside the program.',
        "Only Stack, Card, Grid, Heading, Text, Link, Chart, Map, and Invoice are available. Stack contains at most 24 basic components, cards, or grids, never another Stack. Grid contains up to 20 Cards and adapts from one to two columns. Never nest grids inside cards or grids.",
        "Use Card only for discrete, self-contained items, not every section. Each Card contains at most 24 Heading, Text, Link, Chart, Map, or Invoice components. Never nest cards or stacks inside a Card.",
        "Use Invoice only when the user asks to create an invoice. Its positional arguments are title, amount, currency, creditor, debtor, reference, message, language. Use only user-supplied or explicitly confirmed billing data. Ask for missing names, structured addresses, creditor CH/LI IBAN, amount, and currency before creating it. Never invent or silently change an IBAN, payment reference, amount, or party. Pass address objects with name, address (street only), buildingNumber (empty if absent), zip (string), city, country (uppercase two-letter code); creditor also has account (IBAN). Pass an empty reference for a regular IBAN without a reference; QR-IBAN requires a valid QR reference supplied by the user. Amount must be positive with at most two decimal places. Currency is CHF or EUR. Message is at most 140 characters. Set language to DE, EN, FR, IT, or RM for the conversation language (EN otherwise). The widget creates a preview and downloads a PDF on click; it never sends invoices or makes payments. Tell the user to review all payment details.",
        "For job searches, call ictjobs first, then show one Card per returned job inside Grid. Each job card must contain Heading with the actual job title, Text with the publication date, and Link to that job's exact source URL. Do not substitute a generic website link for actual listings. Include employer, location, salary, or requirements only if returned by a tool; do not claim a geographic filter was applied when it was only a keyword search. Describe the source as the ictjobs.ch API, not scraped data. A successful tool result is not a service failure. If items is empty, say no matching jobs were found. Never request a page beyond total_pages. Render one complete grid, not repeated or contradictory result sections.",
        "Use Map for Swiss locations or canton comparisons using real tool results or user-supplied data only. Never invent coordinates or values. Provide a title, unit (empty for locations only), cantons, and markers; pass [] for unused layers. Canton codes must be unique official two-letter abbreviations. Null and omitted canton values are neutral gray, not zero. All canton values must share the same unit. Marker coordinates are WGS84 longitude/latitude inside Switzerland's bounding box. Localize labels and cite data sources with Link. The bundled canton boundaries are generalized historical outlines from 2016: do not use them to assert current administrative borders or for navigation.",
        'Use Chart for trends (line) or comparisons (bar), using only data returned by tools or supplied by the user. Never invent chart values. Include units in axis labels and cite tool sources with Link when available. Pass series as an array even for one series: [{name: "Temperature", values: [12, null]}]. All series share the same unit. Copy labels and values from the same source rows so they stay aligned; do not invent a full day of hour labels for a shorter forecast. Use null for missing values, not zero. Before emitting a chart, check that each series has one value per label. Limit charts to 100 labels and 4 series. Localize titles, labels, and series names to the conversation language.',
        "Use plain strings in Text and Heading. Link URLs must be HTTP(S), with no embedded credentials. Cite actual official sources, not invented URLs.",
        "Do not use Query, Mutation, actions, reactive variables, functions, HTML, or executable code. Fetch real data using the agent's existing MCP tools before writing the response.",
    ],
    examples: [
        'Only for a user explicitly requesting these fictitious test details, never as default payment data:\n\n```openui-lang\nroot = Stack([Invoice("Invoice TEST-001", 150, "CHF", {name: "Example Consulting AG", address: "Musterstrasse", buildingNumber: "7", zip: "8000", city: "Zürich", country: "CH", account: "CH44 3199 9123 0008 8901 2"}, {name: "Peter Muster", address: "Beispielstrasse", buildingNumber: "12", zip: "3000", city: "Bern", country: "CH"}, "21 00000 00003 13947 14300 09017", "Consulting services - test invoice", "EN")])\n```\n\nTest only. Review all details and do not make a payment.',
        'Layout example using illustrative job data only; always replace with actual tool results:\n\n```openui-lang\nroot = Stack([Heading("Job listings", 2), Grid([Card([Heading("Example developer role", 3), Text("Published 2026-10-24"), Link("View job on ictjobs.ch", "https://ictjobs.ch/example-job/")]), Card([Heading("Example engineering role", 3), Text("Published 2026-10-23"), Link("View job on ictjobs.ch", "https://ictjobs.ch/another-example-job/")])])])\n```',
        'Here is an overview:\n\n```openui-lang\nroot = Stack([Card([Heading("Swiss information", 2), Text("Explore information from official Swiss sources."), Link("Swiss federal portal", "https://www.admin.ch/")])])\n```',
        'Map of user-supplied city coordinates:\n\n```openui-lang\nroot = Stack([Map("Switzerland – Key Cities", "", [], [{label: "Bern", longitude: 7.4474, latitude: 46.948}, {label: "Zürich", longitude: 8.5417, latitude: 47.3769}, {label: "Geneva", longitude: 6.1432, latitude: 46.2044}])])\n```\n\nThe map uses generalized historical canton boundaries, not current administrative or navigation data.',
        'Comparison of illustrative values supplied by the user, not real statistics:\n\n```openui-lang\nroot = Stack([Chart("Illustrative canton values", "bar", "Canton", "%", ["Zürich", "Bern"], [{name: "Illustrative values", values: [80, 60]}])])\n```',
    ],
};

import { defineComponent } from "@openuidev/react-lang";
import { AIMap, mapProps } from "@/components/ai/map";

export const map = defineComponent({
    name: "Map",
    description:
        "A Swiss canton map with optional numeric canton shading and labeled location markers. Supply up to 26 unique two-letter canton codes and 20 markers. Coordinates are WGS84 longitude/latitude within Switzerland's bounding box. Use null for missing canton values; pass empty arrays for unused layers. Boundaries are generalized historical outlines, not current administrative or navigation data.",
    props: mapProps,
    component: AIMap,
});

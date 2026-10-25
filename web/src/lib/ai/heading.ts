import { defineComponent } from "@openuidev/react-lang";
import { AIHeading, headingProps } from "@/components/ai/heading";

export const heading = defineComponent({
    name: "Heading",
    description: "A section heading; level is 2, 3, or 4.",
    props: headingProps,
    component: AIHeading,
});

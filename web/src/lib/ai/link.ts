import { defineComponent } from "@openuidev/react-lang";
import { AILink, linkProps } from "@/components/ai/link";

export const link = defineComponent({
    name: "Link",
    description: "A descriptive link to an HTTP(S) source, without credentials.",
    props: linkProps,
    component: AILink,
});

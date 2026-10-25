import { defineComponent } from "@openuidev/react-lang";
import { AIText, textProps } from "@/components/ai/text";

export const text = defineComponent({
    name: "Text",
    description: "A plain-text paragraph. No HTML or Markdown.",
    props: textProps,
    component: AIText,
});

import { z } from "zod/v4";

export const textProps = z.object({ text: z.string().max(10000) });

export function AIText({ props }: { props: unknown }) {
    const data = textProps.parse(props);
    return <p className="leading-relaxed">{data.text}</p>;
}

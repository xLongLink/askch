import { z } from "zod/v4";

export const headingProps = z.object({
    text: z.string().min(1).max(200),
    level: z.union([z.literal(2), z.literal(3), z.literal(4)]).default(2),
});

export function AIHeading({ props }: { props: unknown }) {
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
}

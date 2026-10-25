import { z } from "zod/v4";

export const linkProps = z.object({
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

export function AILink({ props }: { props: unknown }) {
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
}

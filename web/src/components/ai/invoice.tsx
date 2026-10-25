import { useIsStreaming } from "@openuidev/react-lang";
import { useMemo, useState } from "react";
import { SwissQRBill } from "swissqrbill/svg";
import { isQRIBAN, isSCORReferenceValid } from "swissqrbill/utils";
import { z } from "zod/v4";

const addressProps = z.object({
    name: z.string().trim().min(1).max(70),
    address: z.string().trim().min(1).max(70),
    buildingNumber: z.string().trim().max(16),
    zip: z.string().trim().min(1).max(16),
    city: z.string().trim().min(1).max(35),
    country: z.string().regex(/^[A-Z]{2}$/),
});

export const invoiceProps = z.object({
    title: z.string().trim().min(1).max(120),
    amount: z.number().finite().positive().max(999999999.99).multipleOf(0.01),
    currency: z.enum(["CHF", "EUR"]),
    creditor: addressProps.extend({
        account: z.string().trim().min(21).max(34),
    }),
    debtor: addressProps,
    reference: z.string().trim().max(35),
    message: z.string().trim().max(140),
    language: z.enum(["DE", "EN", "FR", "IT", "RM"]),
});

export function AIInvoice({ props }: { props: unknown }) {
    const isStreaming = useIsStreaming();
    const [downloading, setDownloading] = useState(false);
    const [error, setError] = useState<string>();

    // Validate complete payment details before rendering or enabling a download.
    const invoice = useMemo(() => {
        const result = invoiceProps.safeParse(props);
        if (!result.success) return { error: "Incomplete or invalid invoice details." };
        const data = result.data;
        const payment = {
            amount: data.amount,
            currency: data.currency,
            creditor: data.creditor,
            debtor: data.debtor,
            reference: data.reference || undefined,
            message: data.message || undefined,
        };
        try {
            if (
                data.reference &&
                !isQRIBAN(data.creditor.account) &&
                !isSCORReferenceValid(data.reference)
            ) {
                throw new Error(
                    "A regular IBAN requires a valid RF creditor reference or no reference.",
                );
            }
            const bill = new SwissQRBill(payment, { language: data.language });
            return { data, payment, preview: bill.toString() };
        } catch (error) {
            return { error: error instanceof Error ? error.message : "Invalid payment details." };
        }
    }, [props]);

    // Do not show or download a payment slip while the model is still changing it.
    if (isStreaming) return <p role="status">Preparing invoice…</p>;
    if (!invoice.data) return <p role="alert">Cannot create invoice: {invoice.error}</p>;
    const { data, payment, preview } = invoice;
    const total = `${data.currency} ${data.amount.toFixed(2)}`;

    return (
        <figure className="m-0 min-w-0 space-y-4" aria-label={data.title}>
            <div className="relative overflow-hidden rounded-lg border bg-background text-foreground">
                <div className="space-y-6 p-6">
                    <h3 className="text-xl font-semibold tracking-tight">{data.title}</h3>
                    <dl className="grid gap-6 sm:grid-cols-2">
                        {[data.creditor, data.debtor].map((address, index) => (
                            <div key={index}>
                                <dt className="mb-2 text-sm text-muted-foreground">
                                    {index === 0 ? "From" : "Bill to"}
                                </dt>
                                <dd>
                                    <p className="font-medium">{address.name}</p>
                                    <p>
                                        {address.address} {address.buildingNumber}
                                    </p>
                                    <p>
                                        {address.zip} {address.city}
                                    </p>
                                    <p>{address.country}</p>
                                </dd>
                            </div>
                        ))}
                    </dl>
                    {data.message && <p>{data.message}</p>}
                    <dl className="space-y-3 border-t pt-4">
                        <div className="flex flex-wrap justify-between gap-2 font-semibold">
                            <dt>Total</dt>
                            <dd>{total}</dd>
                        </div>
                        <div>
                            <dt className="text-sm text-muted-foreground">IBAN</dt>
                            <dd>{data.creditor.account}</dd>
                        </div>
                        {data.reference && (
                            <div>
                                <dt className="text-sm text-muted-foreground">Reference</dt>
                                <dd>{data.reference}</dd>
                            </div>
                        )}
                    </dl>
                </div>
                <img
                    src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(preview)}`}
                    alt={`QR payment slip: ${total} to ${data.creditor.name}, IBAN ${data.creditor.account}${data.reference ? `, reference ${data.reference}` : ""}`}
                    className="h-auto w-full border-t"
                />
                <button
                    type="button"
                    className="absolute inset-0 cursor-pointer rounded-lg focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring disabled:cursor-wait"
                    aria-label={`Download ${data.title} as PDF`}
                    aria-busy={downloading}
                    disabled={downloading}
                    onClick={async () => {
                        setDownloading(true);
                        setError(undefined);
                        try {
                            // Load PDFKit only when a user explicitly requests the invoice file.
                            const [{ default: PDFDocument }, { SwissQRBill }] = await Promise.all([
                                import("pdfkit/js/pdfkit.standalone.js"),
                                import("swissqrbill/pdf"),
                            ]);
                            const pdf = new PDFDocument({ size: "A4", margin: 40 });
                            const bill = new SwissQRBill(payment, { language: data.language });
                            const chunks: Uint8Array<ArrayBuffer>[] = [];
                            const document = new Promise<Blob>((resolve, reject) => {
                                pdf.on("data", (chunk: Uint8Array) =>
                                    chunks.push(new Uint8Array(chunk)),
                                );
                                pdf.on("error", reject);
                                pdf.on("end", () =>
                                    resolve(new Blob(chunks, { type: "application/pdf" })),
                                );
                            });

                            // Keep the invoice summary above the full-size QR payment section.
                            pdf.fontSize(20).text(data.title, 40, 40, { width: 515, height: 65 });
                            for (const [index, address] of [data.creditor, data.debtor].entries()) {
                                pdf.fontSize(11).text(
                                    `${address.name}\n${address.address} ${address.buildingNumber}\n${address.zip} ${address.city}\n${address.country}`,
                                    40 + index * 270,
                                    125,
                                    { width: 245, height: 120 },
                                );
                            }
                            pdf.fontSize(12).text(data.message, 40, 270, {
                                width: 515,
                                height: 80,
                            });
                            pdf.fontSize(18).text(total, 40, 375);
                            bill.attachTo(pdf);
                            pdf.end();

                            // Release the download URL after handing the file to the browser.
                            const blob = await document;
                            const url = URL.createObjectURL(blob);
                            try {
                                const link = window.document.createElement("a");
                                link.href = url;
                                link.download = "invoice.pdf";
                                link.click();
                            } finally {
                                URL.revokeObjectURL(url);
                            }
                        } catch {
                            setError("The PDF could not be created. Please try again.");
                        } finally {
                            setDownloading(false);
                        }
                    }}
                >
                    <span className="sr-only">
                        {downloading ? "Creating PDF…" : "Download invoice PDF"}
                    </span>
                </button>
            </div>
            {error && <p role="alert">{error}</p>}
        </figure>
    );
}

import { defineComponent } from "@openuidev/react-lang";
import { AIInvoice, invoiceProps } from "@/components/ai/invoice";

export const invoice = defineComponent({
    name: "Invoice",
    description:
        "A Swiss QR invoice with payment-slip preview and a user-triggered PDF download. Use only billing details supplied or confirmed by the user. Requires title, amount, CHF/EUR, creditor with CH/LI IBAN, debtor, reference (empty if unused), message (empty if unused), and DE/EN/FR/IT/RM language. Addresses are structured: name, street address, buildingNumber (empty if absent), zip, city, two-letter country. Invalid IBANs and incompatible references are rejected. Does not send an invoice or execute a payment.",
    props: invoiceProps,
    component: AIInvoice,
});

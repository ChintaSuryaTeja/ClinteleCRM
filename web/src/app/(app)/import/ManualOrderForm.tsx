"use client";

import { useRouter } from "next/navigation";
import { useRef, useState, useTransition, type FormEvent } from "react";

import { Button, ErrorNotice, TextField } from "@/components/ui";

type Line = { product_code: string; product_name: string; quantity: string; unit_price: string };

/**
 * One order typed in by hand. The API checks it with the same rules as a file
 * and imports it as a one-order upload, so it shows up in Past imports.
 *
 * This form handles submit itself (instead of a form action) so a mistake
 * doesn't wipe everything already typed.
 */
export function ManualOrderForm() {
  const router = useRouter();
  const form = useRef<HTMLFormElement>(null);
  // Each product row needs a stable key; the numbers only identify rows on screen.
  const [rows, setRows] = useState([0]);
  const [nextRow, setNextRow] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [added, setAdded] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function addRow() {
    setRows([...rows, nextRow]);
    setNextRow(nextRow + 1);
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const text = (name: string) => String(data.get(name) ?? "").trim();
    const optional = (name: string) => text(name) || null;
    const body = {
      order_id: text("order_id"),
      order_date: text("order_date"),
      customer_id: text("customer_id"),
      customer_name: optional("customer_name"),
      customer_email: optional("customer_email"),
      lines: rows.map((row): Line => ({
        product_code: text(`product_code_${row}`),
        product_name: text(`product_name_${row}`),
        quantity: text(`quantity_${row}`),
        unit_price: text(`unit_price_${row}`),
      })),
    };

    startTransition(async () => {
      setError(null);
      setAdded(null);
      const response = await fetch("/api/imports/manual", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }).catch(() => null);
      if (response?.ok) {
        setAdded(body.order_id);
        form.current?.reset();
        setRows([0]);
        router.refresh();
        return;
      }
      const result = await response?.json().catch(() => null);
      setError(
        typeof result?.detail === "string"
          ? result.detail
          : "The order wasn't added. Check the fields and try again.",
      );
    });
  }

  return (
    <form ref={form} onSubmit={submit} className="flex flex-col gap-5">
      {error && <ErrorNotice>{error}</ErrorNotice>}
      {added && (
        <p role="status" className="rounded-md bg-canvas px-3 py-2 text-sm">
          Order {added} added. The dashboard includes it within a few seconds.
        </p>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <TextField id="order_id" name="order_id" label="Order ID" required maxLength={100} />
        <TextField id="order_date" name="order_date" type="date" label="Order date" required />
        <TextField
          id="customer_id"
          name="customer_id"
          label="Customer ID"
          required
          maxLength={100}
        />
        <TextField
          id="customer_name"
          name="customer_name"
          label="Customer name (optional)"
          maxLength={200}
        />
        <TextField
          id="customer_email"
          name="customer_email"
          type="email"
          label="Customer email (optional)"
          maxLength={320}
        />
      </div>

      <fieldset className="flex flex-col gap-3">
        <legend className="mb-2 text-sm font-medium">Products in this order</legend>
        {rows.map((row, index) => (
          <div
            key={row}
            className="grid grid-cols-2 items-end gap-3 border-t border-line pt-3 first:border-t-0 first:pt-0 sm:grid-cols-[1fr_1.5fr_0.6fr_0.8fr_auto]"
          >
            <TextField
              id={`product_code_${row}`}
              name={`product_code_${row}`}
              label="Product code"
              required
              maxLength={64}
            />
            <TextField
              id={`product_name_${row}`}
              name={`product_name_${row}`}
              label="Product name (optional)"
            />
            <TextField
              id={`quantity_${row}`}
              name={`quantity_${row}`}
              type="number"
              min={1}
              step={1}
              label="Quantity"
              required
            />
            <TextField
              id={`unit_price_${row}`}
              name={`unit_price_${row}`}
              type="number"
              min={0}
              step="any"
              label="Unit price"
              required
            />
            {rows.length > 1 ? (
              <Button
                type="button"
                variant="secondary"
                onClick={() => setRows(rows.filter((other) => other !== row))}
                aria-label={`Remove product ${index + 1}`}
              >
                Remove
              </Button>
            ) : (
              <span className="hidden sm:block" />
            )}
          </div>
        ))}
      </fieldset>

      <div className="flex flex-wrap gap-3">
        <Button type="button" variant="secondary" onClick={addRow} disabled={rows.length >= 100}>
          Add another product
        </Button>
        <Button type="submit" disabled={pending}>
          {pending ? "Adding…" : "Add order"}
        </Button>
      </div>
    </form>
  );
}

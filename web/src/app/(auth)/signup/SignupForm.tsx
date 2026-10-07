"use client";

import Link from "next/link";
import { useActionState } from "react";

import { Button, ErrorNotice, SelectField, TextField } from "@/components/ui";
import { postJson } from "@/lib/client-api";

type FormState = { error: string | null; organization_name: string; email: string };
const EMPTY: FormState = { error: null, organization_name: "", email: "" };

const CURRENCIES = [
  ["USD", "US dollar"],
  ["EUR", "Euro"],
  ["GBP", "British pound"],
  ["INR", "Indian rupee"],
  ["CAD", "Canadian dollar"],
  ["AUD", "Australian dollar"],
  ["JPY", "Japanese yen"],
  ["SGD", "Singapore dollar"],
];

export function SignupForm() {
  const [state, formAction, pending] = useActionState(
    async (_previous: FormState, form: FormData): Promise<FormState> => {
      const result = await postJson("/auth/signup", {
        organization_name: form.get("organization_name"),
        currency: form.get("currency"),
        email: form.get("email"),
        password: form.get("password"),
      });
      // React clears the form after submitting; hand back what was typed
      // (except the password) so the fields can be refilled.
      if (!result.ok)
        return {
          error: result.message,
          organization_name: String(form.get("organization_name")),
          email: String(form.get("email")),
        };
      // A full page load, not a client-side navigation: Next.js may have cached
      // pages fetched while the visitor was logged out (or in), which would
      // show the wrong page now that the login has changed.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- deliberate full load (see above)
      window.location.assign("/dashboard");
      return EMPTY;
    },
    EMPTY,
  );

  return (
    <form action={formAction} className="flex flex-col gap-5">
      <div>
        <h1 className="text-lg font-semibold">Create an account</h1>
        <p className="mt-1 text-sm text-muted">You&apos;ll be the admin for your organization.</p>
      </div>
      {state.error && <ErrorNotice>{state.error}</ErrorNotice>}
      <TextField
        id="organization_name"
        name="organization_name"
        defaultValue={state.organization_name}
        label="Organization name"
        autoComplete="organization"
        maxLength={200}
        required
      />
      <SelectField
        id="currency"
        name="currency"
        label="Currency of your sales data"
        defaultValue="USD"
      >
        {CURRENCIES.map(([code, name]) => (
          <option key={code} value={code}>
            {code} – {name}
          </option>
        ))}
      </SelectField>
      <TextField
        id="email"
        name="email"
        defaultValue={state.email}
        type="email"
        label="Your work email"
        autoComplete="email"
        required
      />
      <TextField
        id="password"
        name="password"
        type="password"
        label="Password"
        hint="At least 8 characters."
        autoComplete="new-password"
        minLength={8}
        maxLength={128}
        required
      />
      <Button type="submit" disabled={pending}>
        {pending ? "Creating account…" : "Create account"}
      </Button>
      <p className="text-sm text-muted">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-accent underline underline-offset-2">
          Log in
        </Link>
      </p>
    </form>
  );
}

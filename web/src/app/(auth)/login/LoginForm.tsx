"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useActionState } from "react";

import { Button, ErrorNotice, TextField } from "@/components/ui";
import { postJson } from "@/lib/client-api";

type FormState = { error: string | null; email: string };
const EMPTY: FormState = { error: null, email: "" };

export function LoginForm() {
  const router = useRouter();

  // useActionState runs this function when the form is submitted and gives
  // us what it returns (the form state) plus a "pending" flag.
  const [state, formAction, pending] = useActionState(
    async (_previous: FormState, form: FormData): Promise<FormState> => {
      const result = await postJson("/auth/login", {
        email: form.get("email"),
        password: form.get("password"),
      });
      // React clears the form after submitting; hand back what was typed
      // (except the password) so the fields can be refilled.
      if (!result.ok) return { error: result.message, email: String(form.get("email")) };
      router.replace("/dashboard");
      router.refresh();
      return EMPTY;
    },
    EMPTY,
  );

  return (
    <form action={formAction} className="flex flex-col gap-5">
      <h1 className="text-lg font-semibold">Log in</h1>
      {state.error && <ErrorNotice>{state.error}</ErrorNotice>}
      <TextField
        id="email"
        name="email"
        defaultValue={state.email}
        type="email"
        label="Email"
        autoComplete="email"
        required
      />
      <TextField
        id="password"
        name="password"
        type="password"
        label="Password"
        autoComplete="current-password"
        required
      />
      <Button type="submit" disabled={pending}>
        {pending ? "Logging in…" : "Log in"}
      </Button>
      <p className="text-sm text-muted">
        New here?{" "}
        <Link href="/signup" className="font-medium text-accent underline underline-offset-2">
          Create an account for your organization
        </Link>
      </p>
    </form>
  );
}

/** Calls the API from the browser through the /api rewrite in next.config.ts. */

type Result = { ok: true; data: unknown } | { ok: false; message: string };

export async function postJson(path: string, body?: unknown): Promise<Result> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    return {
      ok: false,
      message: "Couldn't reach the server. Check your connection and try again.",
    };
  }

  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (response.ok) return { ok: true, data };
  if (response.status >= 500) {
    return { ok: false, message: "The server ran into a problem. Try again in a moment." };
  }
  return { ok: false, message: readError(data) };
}

const FIELD_NAMES: Record<string, string> = {
  email: "Email",
  password: "Password",
  organization_name: "Organization name",
};

/** FastAPI sends either {detail: "message"} or {detail: [{loc, msg}, ...]} for invalid fields. */
function readError(data: unknown): string {
  const detail = (data as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const { loc, msg } = detail[0] as { loc: string[]; msg: string };
    const field = FIELD_NAMES[loc.at(-1) ?? ""] ?? "A field";
    return `${field}: ${msg.charAt(0).toLowerCase()}${msg.slice(1)}.`;
  }
  return "That didn't work. Check the form and try again.";
}

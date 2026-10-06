// Must match SESSION_COOKIE in api/app/deps.py.
export const SESSION_COOKIE = "crm_session";

export type Role = "admin" | "viewer";

export type CurrentUser = {
  id: number;
  email: string;
  role: Role;
  organization: { id: number; name: string };
};

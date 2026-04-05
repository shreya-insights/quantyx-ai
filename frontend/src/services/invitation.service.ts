import { api } from "@/lib/axios";
import type { TokenResponse } from "@/types/api.types";

export interface InvitationRecord {
  id: number;
  email: string;
  role: string;
  status: "pending" | "accepted" | "expired" | "revoked";
  expires_at: string;
  invited_by_email: string;
  resend_count: number;
  email_sent_at: string | null;
  created_at: string;
}

export interface BulkInviteItem {
  email: string;
  role: "admin" | "analyst" | "viewer";
}

export interface BulkInviteResult {
  email: string;
  status: "queued" | "error";
  invitation_id: number | null;
  error: string | null;
}

export interface BulkInviteResponse {
  results: BulkInviteResult[];
  sent_count: number;
  error_count: number;
}

export interface ValidateTokenResponse {
  valid: boolean;
  email: string | null;
  company_name: string | null;
  role: string | null;
  expires_at: string | null;
}

export interface AcceptInvitePayload {
  token: string;
  full_name: string;
  password: string;
}

export const invitationService = {
  send: (email: string, role: string) =>
    api
      .post<InvitationRecord>("/invitations/send", { email, role })
      .then((r) => r.data),

  sendBulk: (invites: BulkInviteItem[]) =>
    api
      .post<BulkInviteResponse>("/invitations/send-bulk", { invites })
      .then((r) => r.data),

  list: (status?: string) =>
    api
      .get<InvitationRecord[]>("/invitations", {
        params: status ? { status } : undefined,
      })
      .then((r) => r.data),

  resend: (invitationId: number) =>
    api
      .post<InvitationRecord>(`/invitations/${invitationId}/resend`)
      .then((r) => r.data),

  revoke: (invitationId: number) =>
    api.delete(`/invitations/${invitationId}`).then((r) => r.data),

  validate: (token: string) =>
    api
      .get<ValidateTokenResponse>("/invitations/validate", {
        params: { token },
      })
      .then((r) => r.data),

  accept: (payload: AcceptInvitePayload) =>
    api
      .post<TokenResponse>("/invitations/accept", payload)
      .then((r) => r.data),
};

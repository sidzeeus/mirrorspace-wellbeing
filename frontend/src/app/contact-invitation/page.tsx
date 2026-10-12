"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { z } from "zod";

import { AuthPage } from "@/components/AuthPage";
import { Button, Notice } from "@/components/ui/primitives";
import { ApiError, api } from "@/lib/api";
import { useFragment } from "@/lib/fragment";
import { useErrorText } from "@/lib/hooks";

const invitationSchema = z.object({
  from_name: z.string(),
  status: z.string(),
  what_you_may_receive: z.array(z.string()),
  limits: z.string(),
});

/**
 * What a trusted contact sees when they open the invitation link. They have no
 * account: the token from their email, sent in the request body, is the only proof.
 * Nothing is sent to them unless they press "I agree".
 */
export default function ContactInvitationPage() {
  const t = useTranslations("contact.invitation");
  const errorText = useErrorText();
  const fragment = useFragment();
  const token = fragment?.get("token") ?? null;

  const invitation = useQuery({
    queryKey: ["invitation", token],
    queryFn: () =>
      api("/contact-invitations/view", { method: "POST", body: { token }, schema: invitationSchema }),
    enabled: Boolean(token),
    retry: false,
  });
  const answer = useMutation({
    mutationFn: (choice: "accept" | "decline") =>
      api(`/contact-invitations/${choice}`, { method: "POST", body: { token } }).then(() => choice),
  });

  const data = invitation.data;
  return (
    <AuthPage title={t("title")}>
      {fragment !== null && !token ? (
        <Notice tone="attention" role="alert">
          {t("missing")}
        </Notice>
      ) : invitation.isError ? (
        <Notice tone="attention" role="alert">
          {invitation.error instanceof ApiError && invitation.error.code === "invalid_link"
            ? t("invalid")
            : errorText(invitation.error)}
        </Notice>
      ) : answer.isSuccess ? (
        <Notice tone="saved" role="status">
          {answer.data === "accept" ? t("accepted") : t("declined")}
        </Notice>
      ) : data ? (
        <div className="space-y-5">
          <p className="text-lg">
            {data.from_name ? t("from", { name: data.from_name }) : t("fromUnknown")}
          </p>
          <div>
            <p className="mb-2 font-medium">{t("what")}</p>
            <ul className="list-disc space-y-1 pl-5 text-dim">
              {data.what_you_may_receive.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </div>
          <p className="text-dim">{data.limits}</p>
          {data.status === "pending" ? (
            <>
              {answer.isError ? (
                <Notice tone="attention" role="alert">
                  {errorText(answer.error)}
                </Notice>
              ) : null}
              <div className="grid gap-3 sm:grid-cols-2">
                <Button busy={answer.isPending} onClick={() => answer.mutate("accept")}>
                  {t("accept")}
                </Button>
                <Button variant="quiet" busy={answer.isPending} onClick={() => answer.mutate("decline")}>
                  {t("decline")}
                </Button>
              </div>
            </>
          ) : (
            <Notice role="status">{data.status === "confirmed" ? t("alreadyAccepted") : t("closed")}</Notice>
          )}
        </div>
      ) : null}
    </AuthPage>
  );
}

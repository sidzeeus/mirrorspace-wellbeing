/**
 * Shapes of API responses, written to match the OpenAPI schema at /api/v1/schema
 * (see docs/api.md). Parsing responses with these catches a drifting API early and
 * gives every screen real types.
 */
import { z } from "zod";

const nullableScale = z.number().int().min(1).max(5).nullable();

export const meSchema = z.object({
  id: z.string(),
  email: z.string(),
  email_verified: z.boolean(),
  preferred_language: z.string(),
  display_name: z.string(),
  timezone: z.string(),
  created_at: z.string(),
});
export type Me = z.infer<typeof meSchema>;

export const resourceSchema = z.object({
  id: z.string(),
  slug: z.string(),
  name: z.string(),
  description: z.string(),
  type: z.enum(["helpline", "emergency", "text_line", "campus", "online"]),
  region: z.string(),
  languages: z.array(z.string()),
  phone: z.string(),
  url: z.string(),
  hours: z.string(),
  source: z.string(),
  verified_on: z.string().nullable(),
  stale: z.boolean(),
  reviewed: z.boolean(),
});
export type Resource = z.infer<typeof resourceSchema>;

export const checkInSchema = z.object({
  id: z.string(),
  local_date: z.string(),
  timezone: z.string(),
  mood: nullableScale,
  sleep_hours: z.string().nullable(),
  sleep_quality: nullableScale,
  energy: nullableScale,
  stress: nullableScale,
  created_at: z.string(),
  updated_at: z.string(),
});
export type CheckIn = z.infer<typeof checkInSchema>;

const seriesPoint = z.object({
  local_date: z.string(),
  mood: z.number().nullable(),
  sleep_hours: z.number().nullable(),
  sleep_quality: z.number().nullable(),
  energy: z.number().nullable(),
  stress: z.number().nullable(),
});
export type SeriesPoint = z.infer<typeof seriesPoint>;

export const patternsSchema = z.object({
  range: z.object({ from: z.string(), to: z.string(), days: z.number() }),
  check_in_days: z.number(),
  series: z.array(seriesPoint),
  weekly: z.array(z.record(z.string(), z.union([z.string(), z.number(), z.null()]))),
  observations: z.array(
    z.object({
      code: z.string(),
      text: z.string(),
      params: z.record(z.string(), z.union([z.string(), z.number()])),
    }),
  ),
  note: z.string(),
});
export type Patterns = z.infer<typeof patternsSchema>;

export const exerciseSchema = z.object({
  id: z.string(),
  slug: z.string(),
  category: z.enum(["grounding", "breathing", "journaling", "planning", "movement", "wind_down"]),
  duration_minutes: z.number(),
  pattern: z.record(z.string(), z.number()),
  title: z.string(),
  summary: z.string(),
  steps: z.array(z.string()),
  language: z.string(),
  hidden: z.boolean(),
  reviewed: z.boolean(),
});
export type Exercise = z.infer<typeof exerciseSchema>;

export const triggerSchema = z.object({
  id: z.string(),
  label: z.string(),
  is_active: z.boolean(),
  preferred_exercise_ids: z.array(z.string()),
  created_at: z.string(),
});
export type Trigger = z.infer<typeof triggerSchema>;

export const episodeSchema = z.object({
  id: z.string(),
  occurred_at: z.string(),
  intensity: z.number(),
  duration_minutes: z.number().nullable(),
  trigger: z.string().nullable(),
  helped_exercise: z.string().nullable(),
  what_helped: z.string(),
  created_at: z.string(),
});
export type Episode = z.infer<typeof episodeSchema>;

export const safetyPlanSchema = z.object({
  warning_signs: z.array(z.string()),
  coping_steps: z.array(z.string()),
  people: z.array(z.string()),
  resource_ids: z.array(z.string()),
  updated_at: z.string().nullable(),
});
export type SafetyPlan = z.infer<typeof safetyPlanSchema>;

export const contactSchema = z.object({
  id: z.string(),
  name: z.string(),
  email: z.string(),
  relationship: z.string(),
  status: z.enum(["pending", "confirmed", "declined", "unsubscribed", "bounced", "unavailable"]),
  invited_at: z.string().nullable(),
  responded_at: z.string().nullable(),
  created_at: z.string(),
});
export type Contact = z.infer<typeof contactSchema>;

export const consentSchema = z.object({
  id: z.string(),
  purpose: z.enum(["privacy_notice", "weekly_summary"]),
  contact: z.string().nullable(),
  scope: z.array(z.string()),
  notice_version: z.string(),
  status: z.enum(["active", "paused", "revoked"]),
  status_reason: z.string(),
  granted_at: z.string(),
  last_confirmed_at: z.string(),
  paused_at: z.string().nullable(),
  revoked_at: z.string().nullable(),
  send_weekday: z.number().nullable(),
  send_hour: z.number().nullable(),
  next_send_at: z.string().nullable(),
});
export type Consent = z.infer<typeof consentSchema>;

const recipient = z.object({ id: z.string(), name: z.string(), email: z.string() });

export const weeklyPreviewSchema = z.object({
  recipient,
  recipient_can_receive: z.boolean(),
  subject: z.string(),
  body: z.string(),
  fields_shared: z.array(z.string()),
  values: z.object({
    display_name: z.string(),
    week_start: z.string(),
    week_end: z.string(),
    check_in_days: z.number(),
  }),
  notice: z.object({
    purpose: z.string(),
    shared: z.array(z.string()),
    never_shared: z.array(z.string()),
    limits: z.array(z.string()),
    control: z.string(),
  }),
  notice_version: z.string(),
  preview_hash: z.string(),
  default_schedule: z.object({ send_weekday: z.number(), send_hour: z.number() }),
  reconfirm_every_days: z.number(),
});
export type WeeklyPreview = z.infer<typeof weeklyPreviewSchema>;

export const sosPreviewSchema = z.object({
  recipient,
  recipient_can_receive: z.boolean(),
  subject: z.string(),
  body: z.string(),
  message_hash: z.string(),
  limits: z.string(),
});
export type SosPreview = z.infer<typeof sosPreviewSchema>;

export const notificationSchema = z.object({
  id: z.string(),
  purpose: z.enum(["contact_invitation", "weekly_summary", "sos"]),
  contact: z.string().nullable(),
  status: z.enum(["pending", "sending", "sent", "cancelled", "failed", "bounced"]),
  status_code: z.string(),
  scheduled_at: z.string(),
  sent_at: z.string().nullable(),
});
export type Notification = z.infer<typeof notificationSchema>;

export const noticesSchema = z.object({
  privacy_notice_version: z.string(),
  weekly_notice_version: z.string(),
});

export function page<T extends z.ZodTypeAny>(item: T) {
  return z.object({
    count: z.number(),
    next: z.string().nullable(),
    previous: z.string().nullable(),
    results: z.array(item),
  });
}

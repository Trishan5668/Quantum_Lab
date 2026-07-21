/** Shared platform foundation types. All timestamps stored as UTC ISO strings. */

export interface PlatformTimestamps {
  createdAt: string;
  updatedAt: string;
  createdBy?: string;
  updatedBy?: string;
}

export type PlatformRole = "student" | "educator" | "admin";

export type AnalyticsEventName =
  | "lesson_started"
  | "lesson_completed"
  | "exercise_attempted"
  | "exercise_passed"
  | "circuit_saved"
  | "circuit_published"
  | "question_posted"
  | "event_registered"
  | "page_view"
  | "feature_used"
  | "search_performed";

export interface AnalyticsEvent {
  id?: string;
  name: AnalyticsEventName;
  uid: string | null;
  sessionId: string;
  properties: Record<string, string | number | boolean>;
  timestamp: string;
}

export interface AuditLogEntry extends PlatformTimestamps {
  id?: string;
  actorUid: string;
  action: string;
  resourceType: string;
  resourceId: string;
  metadata: Record<string, unknown>;
}

export type NotificationKind = "info" | "success" | "warning" | "achievement";

export interface NotificationItem extends PlatformTimestamps {
  id?: string;
  kind: NotificationKind;
  title: string;
  body: string;
  read: boolean;
  link?: string;
}

export interface ActivityItem extends PlatformTimestamps {
  id?: string;
  uid: string;
  verb: string;
  objectType: string;
  objectId: string;
  summary: string;
  metadata: Record<string, unknown>;
}

export interface FeatureFlag {
  id: string;
  enabled: boolean;
  description: string;
  rolloutPercent?: number;
}

export interface SearchResult {
  id: string;
  type: "course" | "lesson" | "exercise" | "path";
  title: string;
  description: string;
  path: string;
  score: number;
}

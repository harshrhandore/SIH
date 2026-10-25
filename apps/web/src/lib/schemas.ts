import type { components } from "@/lib/generated/api";

export type Row = Record<string, unknown>;

export type User = components["schemas"]["UserResponse"];

export type Envelope = { items: Row[]; total: number; [key: string]: unknown };

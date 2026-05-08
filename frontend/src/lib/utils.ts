/**
 * File: frontend/src/lib/utils.ts
 * Purpose: shadcn cn() helper — combines clsx + tailwind-merge for class composition.
 * Category: Frontend / lib (Sprint 57.7 US-B1 Frontend Foundation 1/N)
 *
 * Description:
 *   Standard shadcn boilerplate. Combines clsx (conditional classes) with
 *   tailwind-merge (deduplicate Tailwind utility conflicts e.g. "px-2 px-4"
 *   collapses to "px-4"). Required by all shadcn-style components.
 *
 * Modification History:
 *   - 2026-05-09: Initial creation (Sprint 57.7 US-B1 Day 2 PM)
 */

import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

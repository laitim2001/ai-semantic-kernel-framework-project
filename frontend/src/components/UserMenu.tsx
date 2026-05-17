/**
 * File: frontend/src/components/UserMenu.tsx
 * Purpose: Header avatar dropdown — current user (authStore) + role badges + locale switcher + sign out.
 * Category: Frontend / components / auth-aware
 * Scope: Phase 57 / Sprint 57.8 US-2 → Sprint 57.13 US-A1 (authStore) → US-B3 (Radix DropdownMenu) → US-B5 (i18n)
 *
 * Description:
 *   Avatar circle in AppShellV2's header right slot. Click → menu showing the
 *   signed-in user (display name / email) + role <Badge>s + a language switcher
 *   (one item per SUPPORTED_LOCALES; the active one is marked) + Sign out (calls
 *   logout() — backend /auth/logout + clear authStore + redirect to vendor signout).
 *   Renders null unless authStore.status === "authenticated".
 *
 *   Sprint 57.13 US-B3: replaced the hand-rolled popover with components/ui
 *   <DropdownMenu> (Radix) — focus, keyboard nav, ESC/outside-click close come free.
 *   Sprint 57.13 US-B5: filled the reserved locale-switcher slot — picking a locale
 *   writes localStorage `ipa-locale` + calls i18n.changeLanguage() (survives reload).
 *
 * Created: 2026-05-10 (Sprint 57.8 Day 2)
 * Last Modified: 2026-05-10
 *
 * Modification History:
 *   - 2026-05-17: Sprint 57.19 US-D3 — mockup port (tenant switch fixtures + nav items + role/region + theme toggle); preserves locale switcher + sign out
 *   - 2026-05-10: Sprint 57.13 US-B5 — locale switcher items + i18n the labels
 *   - 2026-05-10: Sprint 57.13 US-B3 — swap custom popover → <DropdownMenu>; add role badges
 *   - 2026-05-10: Sprint 57.13 US-A1 — read authStore.user instead of decoding the JWT; sign out via logout()
 *   - 2026-05-10: Initial creation (Sprint 57.8 US-2)
 *
 * Related:
 *   - frontend/src/components/ui/dropdown-menu.tsx (Radix wrapper)
 *   - frontend/src/features/auth/store/authStore.ts (user + status + roles)
 *   - frontend/src/features/auth/services/authService.ts (logout)
 *   - frontend/src/i18n/index.ts (SUPPORTED_LOCALES + LOCALE_STORAGE_KEY)
 *   - frontend/src/components/AppShellV2.tsx (host via userMenu prop slot)
 */

import { Check, KeyRound, LogOut, Moon, Settings, Sun, User as UserIcon } from "lucide-react";
import type { FC } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { useTheme } from "@/components/ThemeProvider";

import {
  Badge,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui";
import { logout } from "@/features/auth/services/authService";
import { useAuthStore } from "@/features/auth/store/authStore";
import { LOCALE_STORAGE_KEY, SUPPORTED_LOCALES } from "@/i18n";
import { cn } from "@/lib/utils";

// Mockup fixture tenant list — replace with real API in Sprint 57.20+ (Cat 12 tenant feed).
const TENANT_FIXTURES = [
  { id: "t1", name: "acme-prod", region: "ap-east-1", active: true },
  { id: "t2", name: "globex-eu", region: "eu-west-1", active: false },
  { id: "t3", name: "initech-jp", region: "ap-northeast-1", active: false },
];

export const UserMenu: FC = () => {
  const { t, i18n } = useTranslation("common");
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const status = useAuthStore((s) => s.status);
  const user = useAuthStore((s) => s.user);
  const roles = useAuthStore((s) => s.roles);

  if (status !== "authenticated" || user === null) return null;

  const label = user.display_name?.trim() || user.email;
  const initial = label ? label.charAt(0).toUpperCase() : "?";
  const showEmailLine = Boolean(user.display_name?.trim()) && user.email !== label;

  const currentLng = i18n.resolvedLanguage ?? i18n.language;
  const changeLocale = (id: string): void => {
    try {
      window.localStorage.setItem(LOCALE_STORAGE_KEY, id);
    } catch {
      /* localStorage unavailable (private mode) — changeLanguage still works for the session */
    }
    void i18n.changeLanguage(id);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          "inline-flex h-8 w-8 items-center justify-center rounded-full",
          "bg-primary text-primary-foreground text-sm font-medium",
          "hover:opacity-80 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        )}
        aria-label={t("userMenu.label")}
      >
        {initial === "?" ? <UserIcon size={16} /> : initial}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" aria-label={t("userMenu.options")} className="w-64">
        <DropdownMenuLabel className="font-normal">
          <div className="text-xs text-muted-foreground">{t("userMenu.signedInAs")}</div>
          <div className="truncate text-sm font-medium text-foreground">{label}</div>
          {showEmailLine && (
            <div className="truncate text-xs text-muted-foreground">{user.email}</div>
          )}
          {roles.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {roles.map((r) => (
                <Badge key={r} variant="outline">
                  {r}
                </Badge>
              ))}
            </div>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuLabel className="text-[10px] font-normal uppercase tracking-wider text-muted-foreground">
          {t("userMenu.switchTenant")}
        </DropdownMenuLabel>
        {TENANT_FIXTURES.map((tn) => (
          <DropdownMenuItem
            key={tn.id}
            onSelect={() => { /* tenant switch wired Sprint 57.20+ */ }}
            aria-current={tn.active ? "true" : undefined}
          >
            <Check size={14} className={cn(!tn.active && "invisible")} />
            <div className="flex flex-col">
              <span className="text-sm">{tn.name}</span>
              <span className="font-mono text-[10px] text-muted-foreground">{tn.region}</span>
            </div>
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => navigate("/profile")}>
          <UserIcon size={14} />
          {t("userMenu.profile")}
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => navigate("/mfa")}>
          <KeyRound size={14} />
          {t("userMenu.mfa")}
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => navigate("/admin/tenants")}>
          <Settings size={14} />
          {t("userMenu.preferences")}
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={toggleTheme}>
          {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
          {t(theme === "dark" ? "userMenu.themeLight" : "userMenu.themeDark")}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuLabel className="text-[10px] font-normal uppercase tracking-wider text-muted-foreground">
          {t("userMenu.language")}
        </DropdownMenuLabel>
        {SUPPORTED_LOCALES.map((loc) => {
          const isCurrent = currentLng === loc.id;
          return (
            <DropdownMenuItem
              key={loc.id}
              onSelect={() => changeLocale(loc.id)}
              aria-current={isCurrent ? "true" : undefined}
            >
              <Check size={14} className={cn(!isCurrent && "invisible")} />
              {loc.label}
            </DropdownMenuItem>
          );
        })}
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => void logout()} className="text-danger">
          <LogOut size={14} />
          {t("userMenu.signOut")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

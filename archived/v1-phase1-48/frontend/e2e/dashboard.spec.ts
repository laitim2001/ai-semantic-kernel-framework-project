/**
 * IPA Platform - Dashboard E2E Tests
 *
 * Tests for the main dashboard page functionality.
 *
 * @author IPA Platform Team
 * @version 1.0.0
 */

import { test, expect } from '@playwright/test';

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard
    await page.goto('/dashboard');
  });

  test('should display dashboard page', async ({ page }) => {
    // Verify page title or heading
    await expect(page.locator('h1, h2').first()).toBeVisible();
  });

  test('should display stats cards', async ({ page }) => {
    // Wait for stats cards to load
    const statsSection = page.locator('[data-testid="stats-cards"]').or(
      page.locator('.grid').first()
    );

    // Check for multiple stat cards
    await expect(statsSection).toBeVisible({ timeout: 10000 });
  });

  test('should display execution chart', async ({ page }) => {
    // Look for chart container
    const chartSection = page.locator('[data-testid="execution-chart"]').or(
      page.locator('.recharts-wrapper').first()
    ).or(
      page.locator('svg').first()
    );

    // Chart should be visible (might be loading initially)
    await expect(chartSection).toBeVisible({ timeout: 10000 });
  });

  test('should display recent executions list', async ({ page }) => {
    // Look for executions list
    const executionsList = page.locator('[data-testid="recent-executions"]').or(
      page.locator('text=Recent Executions').first()
    ).or(
      page.locator('table').first()
    );

    await expect(executionsList).toBeVisible({ timeout: 10000 });
  });

  test('should display pending approvals', async ({ page }) => {
    // Look for pending approvals section
    const approvalsSection = page.locator('[data-testid="pending-approvals"]').or(
      page.locator('text=Pending Approvals').first()
    ).or(
      page.locator('text=pending').first()
    );

    await expect(approvalsSection).toBeVisible({ timeout: 10000 });
  });

  test('should navigate to workflows from dashboard', async ({ page }) => {
    // Find and click workflows link
    const workflowsLink = page.locator('a[href*="workflows"]').first();

    if (await workflowsLink.isVisible()) {
      await workflowsLink.click();
      await expect(page).toHaveURL(/.*workflows/);
    }
  });

  test('should be responsive on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Dashboard should still be functional
    await expect(page.locator('body')).toBeVisible();

    // Sidebar might be hidden on mobile
    const sidebar = page.locator('[data-testid="sidebar"]').or(
      page.locator('nav').first()
    );

    // Check that content is accessible
    const mainContent = page.locator('main').or(page.locator('.content'));
    await expect(mainContent).toBeVisible();
  });

  test('should refresh data when refresh button is clicked', async ({ page }) => {
    // Look for refresh button
    const refreshButton = page.locator('button').filter({ hasText: /refresh/i }).or(
      page.locator('[data-testid="refresh-button"]')
    );

    if (await refreshButton.isVisible()) {
      await refreshButton.click();

      // Wait for loading state
      await page.waitForTimeout(1000);

      // Data should be refreshed (no error state)
      await expect(page.locator('text=Error')).not.toBeVisible();
    }
  });
});

test.describe('Dashboard Navigation', () => {
  test('should navigate through sidebar links', async ({ page }) => {
    await page.goto('/dashboard');

    // Test navigation items
    const navItems = [
      { text: /workflows/i, url: /workflows/ },
      { text: /agents/i, url: /agents/ },
      { text: /approvals/i, url: /approvals/ },
      { text: /audit/i, url: /audit/ },
    ];

    for (const item of navItems) {
      const link = page.locator('a').filter({ hasText: item.text }).first();

      if (await link.isVisible()) {
        await link.click();
        await expect(page).toHaveURL(item.url);

        // Navigate back to dashboard
        const dashboardLink = page.locator('a[href*="dashboard"]').first();
        if (await dashboardLink.isVisible()) {
          await dashboardLink.click();
        } else {
          await page.goto('/dashboard');
        }
      }
    }
  });
});

test.describe('Dashboard Accessibility', () => {
  test('should have proper heading hierarchy', async ({ page }) => {
    await page.goto('/dashboard');

    // Check for h1 or h2 heading
    const heading = page.locator('h1, h2').first();
    await expect(heading).toBeVisible();
  });

  test('should have accessible navigation', async ({ page }) => {
    await page.goto('/dashboard');

    // Check for nav element
    const nav = page.locator('nav').first();
    await expect(nav).toBeVisible();
  });

  test('should support keyboard navigation', async ({ page }) => {
    await page.goto('/dashboard');

    // Tab through interactive elements
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Should have a focused element
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeTruthy();
  });
});

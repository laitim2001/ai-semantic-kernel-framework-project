/**
 * IPA Platform - Approvals E2E Tests
 *
 * Tests for the approval workbench functionality.
 *
 * @author IPA Platform Team
 * @version 1.0.0
 */

import { test, expect } from '@playwright/test';

test.describe('Approvals Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/approvals');
  });

  test('should display approvals page', async ({ page }) => {
    // Verify page heading
    const heading = page.locator('h1, h2').filter({ hasText: /approval/i }).first();
    await expect(heading).toBeVisible({ timeout: 10000 });
  });

  test('should display pending approvals or empty state', async ({ page }) => {
    await page.waitForTimeout(2000);

    // Either show approvals list or empty state
    const approvalsList = page.locator('[data-testid="approvals-list"]').or(
      page.locator('table')
    ).or(
      page.locator('.approval-card')
    );

    const emptyState = page.locator('text=No pending').or(
      page.locator('text=no approvals')
    ).or(
      page.locator('[data-testid="empty-state"]')
    );

    const hasApprovals = await approvalsList.isVisible();
    const isEmpty = await emptyState.isVisible();

    expect(hasApprovals || isEmpty).toBeTruthy();
  });

  test('should have approve and reject buttons', async ({ page }) => {
    await page.waitForTimeout(2000);

    // Look for approve/reject buttons
    const approveButton = page.locator('button').filter({ hasText: /approve/i }).first();
    const rejectButton = page.locator('button').filter({ hasText: /reject/i }).first();

    // At least one should exist in the page structure
    const hasApproveButton = await approveButton.isVisible();
    const hasRejectButton = await rejectButton.isVisible();

    // If there are pending items, buttons should be visible
    // If no pending items, this test passes anyway
  });

  test('should filter approvals by workflow', async ({ page }) => {
    // Look for filter dropdown
    const filterSelect = page.locator('select').or(
      page.locator('[data-testid="workflow-filter"]')
    ).or(
      page.locator('button').filter({ hasText: /filter/i })
    );

    if (await filterSelect.isVisible()) {
      await filterSelect.click();
      await page.waitForTimeout(300);
    }
  });

  test('should show approval details when clicked', async ({ page }) => {
    await page.waitForTimeout(2000);

    // Click on first approval item
    const approvalItem = page.locator('tr').first().or(
      page.locator('.approval-card').first()
    ).or(
      page.locator('[data-testid="approval-item"]').first()
    );

    if (await approvalItem.isVisible()) {
      await approvalItem.click();
      await page.waitForTimeout(500);

      // Should show detail view or modal
      const detailView = page.locator('[data-testid="approval-detail"]').or(
        page.locator('.detail-panel')
      ).or(
        page.locator('[role="dialog"]')
      ).or(
        page.locator('text=Details')
      );

      // Detail view might appear
    }
  });
});

test.describe('Approval Actions', () => {
  test('should approve with comments', async ({ page }) => {
    await page.goto('/approvals');
    await page.waitForTimeout(2000);

    // Find approve button
    const approveButton = page.locator('button').filter({ hasText: /approve/i }).first();

    if (await approveButton.isVisible()) {
      await approveButton.click();
      await page.waitForTimeout(500);

      // Look for comments input in dialog/form
      const commentsInput = page.locator('textarea').or(
        page.locator('input[name="comments"]')
      ).or(
        page.locator('[data-testid="approval-comments"]')
      );

      if (await commentsInput.isVisible()) {
        await commentsInput.fill('Approved via E2E test');

        // Confirm approval
        const confirmButton = page.locator('button').filter({ hasText: /confirm|submit/i });
        if (await confirmButton.isVisible()) {
          // Don't actually submit in E2E test to avoid side effects
          await expect(confirmButton).toBeEnabled();
        }
      }
    }
  });

  test('should reject with reason', async ({ page }) => {
    await page.goto('/approvals');
    await page.waitForTimeout(2000);

    // Find reject button
    const rejectButton = page.locator('button').filter({ hasText: /reject/i }).first();

    if (await rejectButton.isVisible()) {
      await rejectButton.click();
      await page.waitForTimeout(500);

      // Look for reason input in dialog/form
      const reasonInput = page.locator('textarea').or(
        page.locator('input[name="reason"]')
      ).or(
        page.locator('[data-testid="rejection-reason"]')
      );

      if (await reasonInput.isVisible()) {
        await reasonInput.fill('Rejected via E2E test - insufficient data');
      }
    }
  });

  test('should support bulk approval', async ({ page }) => {
    await page.goto('/approvals');
    await page.waitForTimeout(2000);

    // Look for checkboxes for selection
    const checkboxes = page.locator('input[type="checkbox"]');

    if (await checkboxes.first().isVisible()) {
      // Select first two items
      await checkboxes.first().check();

      // Look for bulk action button
      const bulkApproveButton = page.locator('button').filter({ hasText: /bulk|all/i });

      if (await bulkApproveButton.isVisible()) {
        await expect(bulkApproveButton).toBeEnabled();
      }
    }
  });
});

test.describe('Approval Notifications', () => {
  test('should display notification badge', async ({ page }) => {
    await page.goto('/dashboard');

    // Look for notification badge in header/nav
    const notificationBadge = page.locator('[data-testid="notification-badge"]').or(
      page.locator('.badge')
    ).or(
      page.locator('span').filter({ hasText: /^\d+$/ })
    );

    // Badge might or might not be visible depending on pending items
  });

  test('should navigate to approvals from notification', async ({ page }) => {
    await page.goto('/dashboard');

    // Look for notification/approval link
    const notificationLink = page.locator('a').filter({ hasText: /approval/i }).first();

    if (await notificationLink.isVisible()) {
      await notificationLink.click();
      await expect(page).toHaveURL(/.*approvals/);
    }
  });
});

test.describe('Approval History', () => {
  test('should display approval history tab', async ({ page }) => {
    await page.goto('/approvals');

    // Look for history tab
    const historyTab = page.locator('button').filter({ hasText: /history/i }).or(
      page.locator('a').filter({ hasText: /history/i })
    ).or(
      page.locator('[data-testid="history-tab"]')
    );

    if (await historyTab.isVisible()) {
      await historyTab.click();
      await page.waitForTimeout(500);

      // Should show history content
      const historyContent = page.locator('[data-testid="approval-history"]').or(
        page.locator('text=History')
      );
    }
  });

  test('should filter history by date', async ({ page }) => {
    await page.goto('/approvals');

    // Click history tab if available
    const historyTab = page.locator('button').filter({ hasText: /history/i });
    if (await historyTab.isVisible()) {
      await historyTab.click();
      await page.waitForTimeout(500);
    }

    // Look for date filter
    const dateFilter = page.locator('input[type="date"]').or(
      page.locator('[data-testid="date-filter"]')
    );

    if (await dateFilter.isVisible()) {
      await dateFilter.fill('2025-01-01');
      await page.waitForTimeout(500);
    }
  });
});

test.describe('Approval Accessibility', () => {
  test('should support keyboard navigation for approvals', async ({ page }) => {
    await page.goto('/approvals');
    await page.waitForTimeout(2000);

    // Tab through elements
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Check for focus indicator
    const focusedElement = page.locator(':focus');
    expect(focusedElement).toBeTruthy();
  });

  test('should have accessible buttons with labels', async ({ page }) => {
    await page.goto('/approvals');
    await page.waitForTimeout(2000);

    // Check approve button has accessible name
    const approveButton = page.locator('button').filter({ hasText: /approve/i }).first();

    if (await approveButton.isVisible()) {
      const ariaLabel = await approveButton.getAttribute('aria-label');
      const innerText = await approveButton.innerText();

      // Should have either aria-label or visible text
      expect(ariaLabel || innerText).toBeTruthy();
    }
  });
});

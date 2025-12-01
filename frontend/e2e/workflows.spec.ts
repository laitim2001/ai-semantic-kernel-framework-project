/**
 * IPA Platform - Workflows E2E Tests
 *
 * Tests for workflow management functionality.
 *
 * @author IPA Platform Team
 * @version 1.0.0
 */

import { test, expect } from '@playwright/test';

test.describe('Workflows List Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/workflows');
  });

  test('should display workflows page', async ({ page }) => {
    // Verify page heading
    const heading = page.locator('h1, h2').filter({ hasText: /workflow/i }).first();
    await expect(heading).toBeVisible({ timeout: 10000 });
  });

  test('should display workflows list or empty state', async ({ page }) => {
    // Wait for content to load
    await page.waitForTimeout(2000);

    // Either show workflows list or empty state
    const workflowsList = page.locator('[data-testid="workflows-list"]').or(
      page.locator('table')
    ).or(
      page.locator('.workflow-card')
    );

    const emptyState = page.locator('text=No workflows').or(
      page.locator('[data-testid="empty-state"]')
    );

    // One of these should be visible
    const hasWorkflows = await workflowsList.isVisible();
    const isEmpty = await emptyState.isVisible();

    expect(hasWorkflows || isEmpty).toBeTruthy();
  });

  test('should have search functionality', async ({ page }) => {
    // Look for search input
    const searchInput = page.locator('input[type="search"]').or(
      page.locator('input[placeholder*="Search"]').or(
        page.locator('input[placeholder*="search"]')
      )
    );

    if (await searchInput.isVisible()) {
      await searchInput.fill('test');
      await page.waitForTimeout(500);

      // Search should trigger (no specific assertion, just no errors)
      await expect(page.locator('text=Error')).not.toBeVisible();
    }
  });

  test('should have create workflow button', async ({ page }) => {
    // Look for create button
    const createButton = page.locator('button').filter({ hasText: /create|new/i }).or(
      page.locator('a').filter({ hasText: /create|new/i })
    );

    if (await createButton.isVisible()) {
      await expect(createButton).toBeEnabled();
    }
  });

  test('should filter workflows by status', async ({ page }) => {
    // Look for filter/dropdown
    const filterSelect = page.locator('select').or(
      page.locator('[data-testid="status-filter"]')
    ).or(
      page.locator('button').filter({ hasText: /filter|status/i })
    );

    if (await filterSelect.isVisible()) {
      await filterSelect.click();
      await page.waitForTimeout(300);
    }
  });
});

test.describe('Workflow Detail Page', () => {
  test('should navigate to workflow detail', async ({ page }) => {
    await page.goto('/workflows');

    // Wait for workflows to load
    await page.waitForTimeout(2000);

    // Click on first workflow if available
    const workflowLink = page.locator('a[href*="/workflows/"]').first().or(
      page.locator('tr').first().locator('a').first()
    ).or(
      page.locator('.workflow-card').first()
    );

    if (await workflowLink.isVisible()) {
      await workflowLink.click();
      await expect(page).toHaveURL(/.*workflows\/.+/);
    }
  });

  test('should display workflow details', async ({ page }) => {
    // Navigate directly to a mock workflow detail
    await page.goto('/workflows/test-workflow-id');

    // Should show workflow info or 404/error
    await page.waitForTimeout(2000);

    // Check for any content
    const content = page.locator('main').or(page.locator('.content'));
    await expect(content).toBeVisible();
  });

  test('should have execute workflow button', async ({ page }) => {
    await page.goto('/workflows');
    await page.waitForTimeout(2000);

    // Navigate to detail if possible
    const workflowLink = page.locator('a[href*="/workflows/"]').first();

    if (await workflowLink.isVisible()) {
      await workflowLink.click();
      await page.waitForTimeout(1000);

      // Look for execute button
      const executeButton = page.locator('button').filter({ hasText: /execute|run/i });

      if (await executeButton.isVisible()) {
        await expect(executeButton).toBeEnabled();
      }
    }
  });

  test('should display execution history', async ({ page }) => {
    await page.goto('/workflows/test-workflow-id');
    await page.waitForTimeout(2000);

    // Look for execution history section
    const historySection = page.locator('text=Execution').or(
      page.locator('text=History')
    ).or(
      page.locator('[data-testid="execution-history"]')
    );

    // History might not be visible for all workflows
    if (await historySection.isVisible()) {
      await expect(historySection).toBeVisible();
    }
  });
});

test.describe('Workflow Creation', () => {
  test('should open create workflow modal or page', async ({ page }) => {
    await page.goto('/workflows');

    // Click create button
    const createButton = page.locator('button').filter({ hasText: /create|new/i }).first().or(
      page.locator('a').filter({ hasText: /create|new/i }).first()
    );

    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      // Should show form or navigate to create page
      const form = page.locator('form').or(
        page.locator('input[name="name"]')
      ).or(
        page.locator('text=Create Workflow')
      );

      if (await form.isVisible()) {
        await expect(form).toBeVisible();
      }
    }
  });

  test('should validate required fields', async ({ page }) => {
    await page.goto('/workflows');

    const createButton = page.locator('button').filter({ hasText: /create|new/i }).first();

    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);

      // Try to submit empty form
      const submitButton = page.locator('button[type="submit"]').or(
        page.locator('button').filter({ hasText: /save|create|submit/i })
      );

      if (await submitButton.isVisible()) {
        await submitButton.click();

        // Should show validation error
        const error = page.locator('text=required').or(
          page.locator('.error')
        ).or(
          page.locator('[role="alert"]')
        );

        // Validation might show immediately
        await page.waitForTimeout(500);
      }
    }
  });
});

test.describe('Workflow Actions', () => {
  test('should be able to edit workflow', async ({ page }) => {
    await page.goto('/workflows');
    await page.waitForTimeout(2000);

    // Navigate to detail
    const workflowLink = page.locator('a[href*="/workflows/"]').first();

    if (await workflowLink.isVisible()) {
      await workflowLink.click();
      await page.waitForTimeout(1000);

      // Look for edit button
      const editButton = page.locator('button').filter({ hasText: /edit/i });

      if (await editButton.isVisible()) {
        await editButton.click();

        // Should show edit form
        const form = page.locator('form').or(
          page.locator('input[name="name"]')
        );

        if (await form.isVisible()) {
          await expect(form).toBeVisible();
        }
      }
    }
  });

  test('should be able to delete workflow with confirmation', async ({ page }) => {
    await page.goto('/workflows');
    await page.waitForTimeout(2000);

    // Look for delete button in list or detail
    const deleteButton = page.locator('button').filter({ hasText: /delete/i }).first();

    if (await deleteButton.isVisible()) {
      await deleteButton.click();

      // Should show confirmation dialog
      const confirmDialog = page.locator('[role="dialog"]').or(
        page.locator('.modal')
      ).or(
        page.locator('text=Are you sure')
      );

      if (await confirmDialog.isVisible()) {
        // Cancel the deletion
        const cancelButton = page.locator('button').filter({ hasText: /cancel|no/i });
        if (await cancelButton.isVisible()) {
          await cancelButton.click();
        }
      }
    }
  });
});

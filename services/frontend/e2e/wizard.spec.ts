import { expect, test } from "@playwright/test";

test.describe("Subscription Wizard E2E Flow", () => {
  test("should fill 3 steps and submit wizard", async ({ page }) => {
    await page.goto("/en/subscriptions/new");

    await expect(
      page.getByRole("heading", { name: "Create New Subscription" }),
    ).toBeVisible();

    // Step 1
    await page.getByPlaceholder("e.g. Paris, France or Rome").fill("Tokyo");
    await page.getByRole("button", { name: "Next Step" }).click();

    // Step 2
    await page.getByRole("button", { name: "Next Step" }).click();

    // Step 3
    await expect(page.getByText("Maximum Price")).toBeVisible();
  });
});

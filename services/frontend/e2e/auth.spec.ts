import { expect, test } from "@playwright/test";

test.describe("Authentication E2E Flow", () => {
  test("should display login form and navigate to register page", async ({
    page,
  }) => {
    await page.goto("/en/login");

    await expect(
      page.getByRole("heading", { name: "Welcome back" }),
    ).toBeVisible();
    await expect(page.getByPlaceholder("alex@example.com")).toBeVisible();

    // Click register link
    await page.getByRole("link", { name: "Sign up" }).click();
    await expect(page).toHaveURL(/\/en\/register/);
    await expect(
      page.getByRole("heading", { name: "Create an account" }),
    ).toBeVisible();
  });
});

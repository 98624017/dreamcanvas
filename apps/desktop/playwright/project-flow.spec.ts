import { expect, test } from "@playwright/test";

const API_BASE = "http://127.0.0.1:18500";

function toJson(body: unknown) {
  return JSON.stringify(body, null, 2);
}

test.describe("项目核心流程", () => {
  test("提交生成任务后任务面板与素材库更新", async ({ page }) => {
    const taskId = "task-e2e-001";
    let pollCount = 0;

    await page.route(`${API_BASE}/healthz`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: toJson({ status: "ok", phase: "P1", version: "0.2.0" }),
      });
    });

    await page.route(`${API_BASE}/jimeng/tasks`, async (route) => {
      const requestBody = await route.request().postDataJSON();
      expect(requestBody.prompt).toContain("未来城市");
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: toJson({
          task: {
            taskId,
            prompt: requestBody.prompt,
            status: "queued",
            metadata: { model: requestBody.model },
            resultUris: [],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        }),
      });
    });

    await page.route(/http:\/\/127\.0\.0\.1:18500\/jimeng\/history.*/, async (route) => {
      pollCount += 1;
      const status = pollCount < 2 ? "running" : "succeeded";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: toJson({
          task: {
            taskId,
            prompt: "渲染未来城市",
            status,
            metadata: { model: "sdxl" },
            resultUris: status === "succeeded" ? ["data:image/png;base64,AAA"] : [],
            errorCode: null,
            errorMessage: null,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        }),
      });
    });

    await page.goto("/");

    await expect(page.getByText("阶段 P1 · MVP Alpha")).toBeVisible();

    await page.getByPlaceholder("新项目名称").fill("E2E 测试项目");
    await page.getByRole("button", { name: "新建" }).click();

    await page.getByPlaceholder("描述你想要的画面、风格、灯光...").fill("渲染未来城市天际线");
    await page.getByRole("button", { name: "提交生成" }).click();

    await expect(page.getByText(new RegExp(`任务已提交：${taskId}`))).toBeVisible();

    await expect(page.getByText("成功", { exact: false })).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/生成成功的图片/)).not.toBeVisible();

    await expect(page.getByText(/素材库/)).toBeVisible();
    const assetCard = page.getByRole("article").filter({ hasText: "渲染未来城市" }).first();
    await expect(assetCard).toBeVisible();
  });
});

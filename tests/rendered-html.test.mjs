import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

const templateRoot = new URL("../", import.meta.url);

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the local video dashboard", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>爆款素材工作台<\/title>/i);
  assert.match(html, /正在读取素材库和视频任务/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton/);
});

test("removes starter markers and ignores local project snapshots", async () => {
  const [css, page, layout, packageJson, gitignore] = await Promise.all([
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
    readFile(new URL("../.gitignore", import.meta.url), "utf8"),
  ]);

  assert.match(page, /dashboard-data\.json/);
  assert.match(page, /素材库/);
  assert.match(page, /新建爆款任务/);
  assert.match(page, /创建并开始拆解/);
  assert.match(page, /待提供正式文案/);
  assert.match(layout, /title:\s*"爆款素材工作台"/);
  assert.match(css, /\.asset-grid/);
  assert.match(css, /\.drop-zone/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
  assert.match(gitignore, /public\/dashboard-data\.json/);
  assert.match(gitignore, /public\/local-media/);

  await assert.rejects(access(new URL("app/_sites-preview", templateRoot)));
});

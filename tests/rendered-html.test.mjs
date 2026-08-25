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

test("server-renders the local shot splitter", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>爆款视频拆镜头<\/title>/i);
  assert.match(html, /导入爆款视频/);
  assert.match(html, /原视频预览/);
  assert.match(html, /分镜九宫格/);
  assert.match(html, /开始拆解视频/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton/);
});

test("contains upload, storyboard pagination and clip preview wiring", async () => {
  const [css, page, layout, packageJson, gitignore] = await Promise.all([
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
    readFile(new URL("../.gitignore", import.meta.url), "utf8"),
  ]);

  assert.match(page, /\/api\/tasks/);
  assert.match(page, /\/api\/storyboard\/latest/);
  assert.match(page, /\/api\/media/);
  assert.match(page, /开始拆解视频/);
  assert.match(page, /slice\(\(page - 1\) \* 9, page \* 9\)/);
  assert.match(page, /selectedShot\.clipPath/);
  assert.match(page, /CompositionGrid/);
  assert.match(page, /构图九宫格/);
  assert.match(layout, /title:\s*"爆款视频拆镜头"/);
  assert.match(css, /\.shot-grid/);
  assert.match(css, /\.drop-button/);
  assert.match(css, /\.pagination/);
  assert.match(css, /\.shot-dialog/);
  assert.match(css, /\.composition-grid/);
  assert.match(css, /\.grid-line\.vertical/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
  assert.match(gitignore, /public\/dashboard-data\.json/);
  assert.match(gitignore, /public\/local-media/);

  await assert.rejects(access(new URL("app/_sites-preview", templateRoot)));
});

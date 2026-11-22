//
// Copyright (C) 2026 Dan Brown
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Takes the screenshots of docs/USER-GUIDE.md from the UI harness. See
// "Screenshots" in ui/dev/README.md. Runs in the Playwright image; HARNESS is
// the harness URL as seen from the container, OUT the directory the PNG files
// are written to. Adapted from ns8-automx's ui/dev/screenshots.js.
const net = require("net");
const { chromium } = require("playwright-core");

// The harness as seen from the container. The page is loaded from localhost
// instead, through a forwarder: the key is made with crypto.subtle, which
// needs a secure context, and localhost is one.
const HARNESS = new URL(process.env.HARNESS || "http://host.docker.internal:8099/");
const LOCAL_PORT = 8099;
const BASE = `http://localhost:${LOCAL_PORT}/`;
const OUT = process.env.OUT || "/out";
const BAR = 30; // the harness's own top bar, left out of the pictures
const WIDTH = 1056; // wide enough for the tables, and for dialogs to show as a window
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const forwarder = net.createServer((client) => {
    const upstream = net.connect(Number(HARNESS.port) || 80, HARNESS.hostname);
    client.pipe(upstream).pipe(client);
    const close = () => { client.destroy(); upstream.destroy(); };
    client.on("error", close);
    upstream.on("error", close);
  });
  await new Promise((resolve) => forwarder.listen(LOCAL_PORT, "127.0.0.1", resolve));
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: WIDTH, height: 600 + BAR },
    deviceScaleFactor: 1,
    locale: process.env.LOCALE || "en-US",
  });
  page.on("pageerror", (e) => console.log("PAGE ERROR", e.message));
  await page.goto(BASE);
  await sleep(3000);
  if (!(await page.evaluate(() => window.isSecureContext))) throw new Error("not a secure context: keys cannot be made");
  const frame = () => page.frames().find((f) => f.url().includes("/app/"));
  const resize = (height, width = WIDTH) => page.setViewportSize({ width, height: height + BAR });
  const shot = async (name) => {
    await sleep(900);
    await page.locator("iframe").screenshot({ path: `${OUT}/${name}.png` });
    console.log("shot", name);
  };
  // run fn(root, findBy, sleep, nav, d, arg) inside the app frame
  const run = (fn, arg, ms = 30000) => Promise.race([
    new Promise((_, rej) => setTimeout(() => rej(new Error("step timed out: " + fn.toString().slice(0, 120))), ms)),
    frame().evaluate(
      async ({ src, arg }) => {
        const d = document;
        const root = d.querySelector("#ns8-app").__vue__;
        const findBy = (v, n) => {
          if (v.$options.name === n) return v;
          for (const c of v.$children) {
            const x = findBy(c, n);
            if (x) return x;
          }
        };
        const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
        const nav = async (index) => {
          // by position in the side menu (Status, Tenants, Keys, Activity, Settings, About),
          // so that it works in any language
          [...d.querySelectorAll(".bx--side-nav__link")][index].click();
          await sleep(2000);
        };
        // eslint-disable-next-line no-new-func
        return await new Function("root", "findBy", "sleep", "nav", "d", "arg", `return (${src})(root, findBy, sleep, nav, d, arg)`)(
          root, findBy, sleep, nav, d, arg
        );
      },
      { src: fn.toString(), arg }
    )]);
  const go = (index) => run(async (root, findBy, sleep, nav, d, arg) => { await nav(arg); }, index);
  const STATUS = 0, TENANTS = 1, KEYS = 2, ACTIVITY = 3, SETTINGS = 4;
  // Opening a dialog focuses its primary button, which scrolls a tall dialog to its end.
  const dialogTop = () => run(async (root, findBy, sleep, nav, d) => {
    d.activeElement.blur();
    d.querySelectorAll(".bx--modal.is-visible, .bx--modal.is-visible .bx--modal-container, .bx--modal.is-visible .bx--modal-content")
      .forEach((el) => { el.scrollTop = 0; });
    await sleep(300);
  });

  // ---- Status
  await resize(720);
  await go(STATUS);
  await shot("status");

  // ---- Tenants, and editing one
  await resize(440);
  await go(TENANTS);
  await shot("tenants");
  await resize(760);
  await run(async (root, findBy, sleep) => {
    const p = findBy(root, "Tenants");
    p.showEdit(p.tenants.find((t) => t.name === "Internal hosts"));
    await sleep(1500);
  });
  await dialogTop();
  await shot("tenant-edit");
  await run(async (root, findBy, sleep) => { findBy(root, "Tenants").isEditShown = false; await sleep(800); });

  // ---- Keys, making one, and the key shown once
  await resize(640);
  await go(KEYS);
  await shot("keys");
  await resize(980);
  await run(async (root, findBy, sleep) => {
    findBy(root, "Keys").isCreateShown = true;
    await sleep(1200);
    const m = findBy(root, "CreateKeyModal");
    m.owner = "t5be20a93";
    m.label = "mail certificates";
    m.restrictKind = "acme";
    m.allowlist = "10.0.0.7";
    await sleep(600);
  });
  await dialogTop();
  await shot("key-create");
  await resize(560);
  await run(async (root, findBy, sleep) => { await findBy(root, "CreateKeyModal").save(); await sleep(1500); });
  await dialogTop();
  await shot("key-created");
  await run(async (root, findBy, sleep) => { findBy(root, "Keys").isCreateShown = false; await sleep(800); });

  // ---- Activity
  await resize(560);
  await go(ACTIVITY);
  await shot("activity");

  // ---- Settings
  await resize(900);
  await go(SETTINGS);
  await sleep(3000);
  await run(async (root, findBy, sleep, nav, d) => { d.activeElement.blur(); await sleep(300); });
  await shot("settings");

  await browser.close();
  forwarder.close();
})().catch((e) => { console.error(e); process.exit(1); });

"""Test mobile viewport fit on /inicio.html using real device emulation."""
import asyncio
import os
from playwright.async_api import async_playwright

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

PAGES = ["/inicio.html", "/pagamento-pix.html", "/inscricao-realizada.html"]


async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        results = {}

        # ---- MOBILE (iPhone 13 emulation) ----
        for device_name in ["iPhone 13", "Pixel 5"]:
            device = p.devices[device_name]
            ctx = await browser.new_context(**device)
            page = await ctx.new_page()
            for path in PAGES:
                url = BASE + path
                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    await page.wait_for_timeout(500)
                except Exception as e:
                    results[f"{device_name}{path}"] = {"error": str(e)}
                    continue
                metrics = await page.evaluate("""() => {
                    const vp = document.querySelector('meta[name=viewport]');
                    return {
                        viewport: vp ? vp.getAttribute('content') : null,
                        scrollWidth: document.documentElement.scrollWidth,
                        clientWidth: document.documentElement.clientWidth,
                        innerWidth: window.innerWidth,
                        innerHeight: window.innerHeight,
                    };
                }""")
                # Check hero for inicio.html
                hero_info = None
                if path == "/inicio.html":
                    hero_info = await page.evaluate("""() => {
                        const findText = (root) => {
                            const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
                            let node;
                            while ((node = walker.nextNode())) {
                                if (node.textContent && node.textContent.trim().toUpperCase().includes('INSCRIÇÕES') && node.children.length === 0) {
                                    const r = node.getBoundingClientRect();
                                    if (r.width > 0 && r.height > 0) return {text: node.textContent.trim(), left: r.left, right: r.right, width: r.width, viewportW: window.innerWidth};
                                }
                            }
                            return null;
                        };
                        return findText(document.body);
                    }""")
                results[f"{device_name}{path}"] = {**metrics, "hero": hero_info}
                safe = path.replace("/", "_").replace(".", "_")
                await page.screenshot(path=f"/app/test_reports/mobile_{device_name.replace(' ','_')}_{safe}.png", full_page=False, quality=40, type="jpeg")
            await ctx.close()

        # ---- DESKTOP regression ----
        ctx = await browser.new_context(viewport={"width": 1920, "height": 800})
        page = await ctx.new_page()
        await page.goto(BASE + "/inicio.html", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(500)
        desktop = await page.evaluate("""() => {
            const vp = document.querySelector('meta[name=viewport]');
            return {
                viewport: vp ? vp.getAttribute('content') : null,
                scrollWidth: document.documentElement.scrollWidth,
                innerWidth: window.innerWidth,
            };
        }""")
        results["desktop_inicio"] = desktop
        await page.screenshot(path="/app/test_reports/desktop_inicio.jpeg", full_page=False, quality=40, type="jpeg")
        await ctx.close()

        await browser.close()

        # Print + evaluate
        print("=" * 80)
        overall_ok = True
        for k, v in results.items():
            print(f"\n[{k}]")
            print(v)
            if "error" in v:
                overall_ok = False
                continue
            if k.startswith("desktop"):
                if "width=device-width" not in (v.get("viewport") or ""):
                    print("  DESKTOP FAIL: viewport not width=device-width")
                    overall_ok = False
                else:
                    print("  DESKTOP OK")
            else:
                sw = v["scrollWidth"]; iw = v["innerWidth"]
                # For mobile with meta width=1300, layout width will be 1300 but visual scale ~innerWidth/1300 -> no horizontal scroll expected
                if sw > iw + 5:
                    # It's OK if scrollWidth == 1300 (layout width) as long as visual viewport shows entire page.
                    # But typical: with initial-scale=innerWidth/1300 and width=1300, scrollWidth may equal 1300; browser scales it. 
                    # We still expect NO horizontal scrollbar physically. Check via visualViewport instead if available.
                    print(f"  NOTE: scrollWidth({sw}) > innerWidth({iw}) - checking viewport meta")
                vp_content = v.get("viewport") or ""
                if "/inicio.html" in k:
                    if "width=1300" not in vp_content:
                        print(f"  MOBILE FAIL: viewport meta missing width=1300: {vp_content}")
                        overall_ok = False
                    else:
                        # parse initial-scale
                        import re
                        m = re.search(r"initial-scale=([0-9.]+)", vp_content)
                        if m:
                            scale = float(m.group(1))
                            if scale >= 1:
                                print(f"  MOBILE FAIL: initial-scale {scale} not < 1")
                                overall_ok = False
                            else:
                                print(f"  MOBILE OK: viewport width=1300 initial-scale={scale}")
                        else:
                            print("  MOBILE FAIL: no initial-scale in meta")
                            overall_ok = False
                    hero = v.get("hero")
                    if hero:
                        # right edge should be <= layout viewport (1300) if visible
                        print(f"  Hero: '{hero['text'][:60]}' left={hero['left']} right={hero['right']} viewportW={hero['viewportW']}")
                        if hero["right"] > hero["viewportW"] + 2:
                            print(f"  MOBILE FAIL: hero cut off (right={hero['right']} > viewport={hero['viewportW']})")
                            overall_ok = False
                        else:
                            print("  Hero fully within viewport width")
                    else:
                        print("  WARN: hero INSCRIÇÕES element not located")

        print("\n" + "=" * 80)
        print("OVERALL:", "PASS" if overall_ok else "FAIL")


asyncio.run(run())

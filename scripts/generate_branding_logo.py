"""Procedural SVG and PNG logo generator for CrawlCraft following developer-branding specifications."""

from pathlib import Path
import asyncio
from playwright.async_api import async_playwright

SVG_CONTENT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
  <defs>
    <clipPath id="squircle-clip">
      <rect x="24" y="24" width="976" height="976" rx="220" />
    </clipPath>

    <linearGradient id="emerald-glow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#34d399"/>
      <stop offset="100%" stop-color="#059669"/>
    </linearGradient>

    <linearGradient id="cyan-accent" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00f5ff"/>
      <stop offset="100%" stop-color="#10b981"/>
    </linearGradient>

    <linearGradient id="obsidian-facet" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>

    <filter id="subtle-shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="16" stdDeviation="20" flood-color="#000000" flood-opacity="0.14" />
    </filter>
  </defs>

  <!-- Luxury White Squircle Container -->
  <rect x="24" y="24" width="976" height="976" rx="220" fill="#ffffff" stroke="#e2e8f0" stroke-width="6" />

  <g clip-path="url(#squircle-clip)">
    <g transform="translate(512, 512)" filter="url(#subtle-shadow)">

      <!-- Hexagonal Architectural Gateway Frame -->
      <polygon points="
        0,-410
        355,-205
        355,205
        0,410
        -355,205
        -355,-205
      " fill="none" stroke="#0f172a" stroke-width="36" stroke-linejoin="round" />

      <!-- Inner High-Tech Emerald Telemetry Dashed Hexagon -->
      <polygon points="
        0,-375
        324,-187
        324,187
        0,375
        -324,187
        -324,-187
      " fill="none" stroke="#10b981" stroke-width="4" opacity="0.45" stroke-dasharray="16, 12" />

      <!-- Concentric Web Geometry Links -->
      <polygon points="0,-270 234,-135 234,135 0,270 -234,135 -234,-135" fill="none" stroke="#0f172a" stroke-width="3" opacity="0.15" />
      <polygon points="0,-160 138,-80 138,80 0,160 -138,80 -138,-80" fill="none" stroke="#10b981" stroke-width="2" opacity="0.25" stroke-dasharray="8, 8" />

      <!-- ARACHNE CORE MASCOT: 85% Width Symmetrical Low-Poly Origami Spider -->

      <!-- 1. Watertight Solid Obsidian Base Silhouette -->
      <path d="
        M 0 -220
        L 55 -170 L 95 -180 L 145 -125 L 120 -80 L 175 -35 L 210 -75 L 290 -160 L 320 -145 L 235 -20 L 330 35 L 340 70 L 225 35 L 295 130 L 290 165 L 195 95 L 225 210 L 210 240 L 140 145 L 110 250 L 0 310
        L -110 250 L -140 145 L -210 240 L -225 210 L -195 95 L -290 165 L -295 130 L -225 35 L -340 70 L -330 35 L -235 -20 L -320 -145 L -290 -160 L -210 -75 L -175 -35 L -120 -80 L -145 -125 L -95 -180 L -55 -170
        Z
      " fill="#0b0f19" />

      <!-- 2. Articulated Low-Poly Spider Legs (Faceted Polygons) -->
      <!-- Front Upper Legs (Pair 1) -->
      <!-- Right Leg 1 -->
      <polygon points="120,-80 210,-75 290,-160 235,-20" fill="#1e293b" />
      <polygon points="290,-160 320,-145 235,-20" fill="#334155" />
      <polygon points="120,-80 235,-20 160,-30" fill="#0f172a" />
      <!-- Left Leg 1 -->
      <polygon points="-120,-80 -210,-75 -290,-160 -235,-20" fill="#334155" />
      <polygon points="-290,-160 -320,-145 -235,-20" fill="#1e293b" />
      <polygon points="-120,-80 -235,-20 -160,-30" fill="#0f172a" />

      <!-- Mid-Upper Legs (Pair 2) -->
      <!-- Right Leg 2 -->
      <polygon points="150,-10 240,15 330,35 225,35" fill="#334155" />
      <polygon points="330,35 340,70 225,35" fill="#1e293b" />
      <polygon points="150,-10 225,35 155,45" fill="#0f172a" />
      <!-- Left Leg 2 -->
      <polygon points="-150,-10 -240,15 -330,35 -225,35" fill="#475569" />
      <polygon points="-330,35 -340,70 -225,35" fill="#334155" />
      <polygon points="-150,-10 -225,35 -155,45" fill="#0f172a" />

      <!-- Mid-Lower Legs (Pair 3) -->
      <!-- Right Leg 3 -->
      <polygon points="140,55 220,80 295,130 195,95" fill="#1e293b" />
      <polygon points="295,130 290,165 195,95" fill="#0f172a" />
      <polygon points="140,55 195,95 130,95" fill="#334155" />
      <!-- Left Leg 3 -->
      <polygon points="-140,55 -220,80 -295,130 -195,95" fill="#334155" />
      <polygon points="-295,130 -290,165 -195,95" fill="#1e293b" />
      <polygon points="-140,55 -195,95 -130,95" fill="#0f172a" />

      <!-- Rear Legs (Pair 4) -->
      <!-- Right Leg 4 -->
      <polygon points="110,110 170,140 225,210 140,145" fill="#334155" />
      <polygon points="225,210 210,240 140,145" fill="#1e293b" />
      <polygon points="110,110 140,145 90,150" fill="#0f172a" />
      <!-- Left Leg 4 -->
      <polygon points="-110,110 -170,140 -225,210 -140,145" fill="#475569" />
      <polygon points="-225,210 -210,240 -140,145" fill="#334155" />
      <polygon points="-110,110 -140,145 -90,150" fill="#0f172a" />

      <!-- 3. Abdomen (Opisthosoma) - Lower Armored Hex Core -->
      <polygon points="0,50 110,105 110,215 0,285 -110,215 -110,105" fill="#064e3b" stroke="#10b981" stroke-width="4" />
      <!-- Abdomen internal volumetric facets -->
      <polygon points="0,50 110,105 0,175" fill="#047857" />
      <polygon points="0,50 -110,105 0,175" fill="#059669" />
      <polygon points="110,105 110,215 0,175" fill="#065f46" />
      <polygon points="-110,105 -110,215 0,175" fill="#047857" />
      <polygon points="110,215 0,285 0,175" fill="#022c22" />
      <polygon points="-110,215 0,285 0,175" fill="#064e3b" />

      <!-- Central Hyper-Speed Shard / Neural Core Emblem -->
      <polygon points="0,100 35,160 0,245 -35,160" fill="url(#cyan-accent)" />
      <polygon points="0,100 0,245 35,160" fill="#00f5ff" opacity="0.6" />

      <!-- 4. Cephalothorax (Prosoma) - Upper Armor & Head -->
      <polygon points="0,-165 95,-120 85,-10 0,40 -85,-10 -95,-120" fill="#0f172a" stroke="#10b981" stroke-width="3" />
      <!-- Volumetric facets on head -->
      <polygon points="0,-165 95,-120 0,-70" fill="#1e293b" />
      <polygon points="0,-165 -95,-120 0,-70" fill="#334155" />
      <polygon points="95,-120 85,-10 0,-70" fill="#0f172a" />
      <polygon points="-95,-120 -85,-10 0,-70" fill="#1e293b" />
      <polygon points="85,-10 0,40 0,-70" fill="#1e293b" />
      <polygon points="-85,-10 0,40 0,-70" fill="#334155" />

      <!-- Chelicerae / Mandibles (Sharp Precision Cutters) -->
      <polygon points="-45,-165 0,-195 -15,-225 -55,-185" fill="#334155" />
      <polygon points="45,-165 0,-195 15,-225 55,-185" fill="#1e293b" />
      <polygon points="0,-195 15,-225 0,-215" fill="#10b981" />
      <polygon points="0,-195 -15,-225 0,-215" fill="#34d399" />

      <!-- 5. 8-Point Geometric Sensor Array (Predator Eyes - Almond Hex Gems) -->
      <!-- Primary Central Eyes -->
      <polygon points="-22,-95 -10,-105 -2,-95 -14,-85" fill="#00f5ff" />
      <polygon points="22,-95 10,-105 2,-95 14,-85" fill="#00f5ff" />
      <!-- Secondary Median Eyes -->
      <polygon points="-26,-75 -15,-82 -8,-75 -19,-68" fill="#34d399" />
      <polygon points="26,-75 15,-82 8,-75 19,-68" fill="#34d399" />
      <!-- Lateral Eyes Upper -->
      <polygon points="-52,-90 -42,-98 -36,-90 -46,-82" fill="#10b981" />
      <polygon points="52,-90 42,-98 36,-90 46,-82" fill="#10b981" />
      <!-- Lateral Eyes Lower -->
      <polygon points="-58,-70 -48,-78 -42,-70 -52,-62" fill="#059669" />
      <polygon points="58,-70 48,-78 42,-70 52,-62" fill="#059669" />

      <!-- Circuit Telemetry Node Accents on Leg Joints -->
      <circle cx="235" cy="-20" r="7" fill="#00f5ff" />
      <circle cx="-235" cy="-20" r="7" fill="#00f5ff" />
      <circle cx="225" cy="35" r="7" fill="#10b981" />
      <circle cx="-225" cy="35" r="7" fill="#10b981" />
      <circle cx="195" cy="95" r="7" fill="#10b981" />
      <circle cx="-195" cy="95" r="7" fill="#10b981" />
      <circle cx="140" cy="145" r="7" fill="#34d399" />
      <circle cx="-140" cy="145" r="7" fill="#34d399" />

    </g>
  </g>
</svg>
"""


async def main():
    images_dir = Path("docs/images")
    images_dir.mkdir(parents=True, exist_ok=True)

    svg_path = images_dir / "crawlcraft_logo.svg"
    svg_path.write_text(SVG_CONTENT.strip(), encoding="utf-8")
    print(f"Written logo SVG to {svg_path}")

    # Render pixel-perfect PNG with Playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1024, "height": 1024})
        await page.set_content(SVG_CONTENT.strip())
        png_path = images_dir / "crawlcraft_logo.png"
        await page.screenshot(path=str(png_path), omit_background=True)
        print(f"Rendered logo PNG to {png_path}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

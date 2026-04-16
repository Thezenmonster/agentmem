"""Generate an animated SVG terminal demo for agentmem README."""

# Each frame: (delay_ms, text, color)
# Colors: #e6edf3=white, #3fb950=green, #58a6ff=blue, #8b949e=gray, #d29922=yellow
FRAMES = [
    (0, "$ ", "#8b949e"),
    (600, "pip install quilmem[mcp]", "#e6edf3"),
    (1800, "\nSuccessfully installed quilmem-0.2.3", "#3fb950"),
    (2600, "\n\n$ ", "#8b949e"),
    (3200, "agentmem init --tool claude --project myapp", "#e6edf3"),
    (4800, "\n\n✓ Created memory database: ./memory.db", "#3fb950"),
    (5400, "\n✓ Added starter memory", "#3fb950"),
    (5900, "\n✓ Health check: 100/100", "#3fb950"),
    (6600, '\n\nAdd this to .claude/settings.json:', "#58a6ff"),
    (7400, '\n\n  { "mcpServers": { "agentmem": {', "#d29922"),
    (7800, '\n      "command": "agentmem",', "#d29922"),
    (8200, '\n      "args": ["--db","./memory.db",', "#d29922"),
    (8500, '\n              "--project","myapp","serve"]', "#d29922"),
    (8800, "\n  }}}", "#d29922"),
    (9600, "\n\nRestart your editor. 13 memory tools ready.", "#58a6ff"),
    (11000, "\n\n$ ", "#8b949e"),
    (11400, "agentmem health", "#e6edf3"),
    (12400, "\n\nMemory Health Report", "#e6edf3"),
    (12700, "\n━━━━━━━━━━━━━━━━━━━━", "#8b949e"),
    (13000, "\nHealth Score:  100/100", "#3fb950"),
    (13300, "\nTotal:         1 memory", "#e6edf3"),
    (13600, "\nConflicts:     0", "#3fb950"),
    (13900, "\nStale:         0", "#3fb950"),
]

WIDTH = 720
HEIGHT = 540
BG = "#0d1117"
BORDER = "#30363d"
FONT_SIZE = 13.5
LINE_HEIGHT = 18
PADDING_X = 20
PADDING_Y = 50  # space for title bar
TOTAL_DURATION = 18000  # ms, includes pause at end

def escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def build_svg():
    lines = []
    # SVG header
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}">')
    lines.append(f'  <rect width="{WIDTH}" height="{HEIGHT}" rx="8" fill="{BG}" stroke="{BORDER}" stroke-width="1"/>')

    # Title bar
    lines.append(f'  <rect width="{WIDTH}" height="32" rx="8" fill="#161b22"/>')
    lines.append(f'  <rect x="0" y="24" width="{WIDTH}" height="8" fill="#161b22"/>')
    lines.append('  <circle cx="16" cy="16" r="5" fill="#f85149"/>')
    lines.append('  <circle cx="34" cy="16" r="5" fill="#d29922"/>')
    lines.append('  <circle cx="52" cy="16" r="5" fill="#3fb950"/>')
    lines.append(f'  <text x="{WIDTH//2}" y="20" text-anchor="middle" font-family="monospace" font-size="12" fill="#8b949e">agentmem demo</text>')

    # Build text spans with animation
    x = PADDING_X
    y = PADDING_Y
    for i, (delay, text, color) in enumerate(FRAMES):
        # Split text by newlines
        parts = text.split("\n")
        for j, part in enumerate(parts):
            if j > 0:
                x = PADDING_X
                y += LINE_HEIGHT
            if part:
                escaped = escape(part)
                # Create text element with fade-in animation
                lines.append(f'  <text x="{x}" y="{y}" font-family="\'SF Mono\',\'Fira Code\',Consolas,monospace" font-size="{FONT_SIZE}" fill="{color}" opacity="0">')
                lines.append(f'    {escaped}')
                lines.append(f'    <animate attributeName="opacity" from="0" to="1" begin="{delay/1000:.1f}s" dur="0.15s" fill="freeze"/>')
                lines.append(f'  </text>')
                x += len(part) * 8.2  # approximate monospace width

    # Loop animation - reset everything
    lines.append(f'  <animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;{(TOTAL_DURATION-1000)/TOTAL_DURATION:.3f};{(TOTAL_DURATION-500)/TOTAL_DURATION:.3f};{(TOTAL_DURATION-100)/TOTAL_DURATION:.3f};1" dur="{TOTAL_DURATION/1000:.1f}s" repeatCount="indefinite"/>')

    lines.append('</svg>')
    return "\n".join(lines)

svg = build_svg()
out = "C:/Users/onyek/Documents/agentmem/assets/demo.svg"
with open(out, "w", encoding="utf-8") as f:
    f.write(svg)
print(f"Written to {out} ({len(svg)} bytes)")

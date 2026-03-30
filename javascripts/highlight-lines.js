// Multi-color code line highlighting with semantic types.
//
// Usage in markdown (requires attr_list + superfences + highlight with line_spans):
//
//   ```{ .python data-exec-yellow="3" data-which-red="7" data-exec-green="10-12" }
//   ...code...
//   ```
//
// Types: exec (► + italic), break (●)
// Colors: red, green, blue, yellow, orange, purple, gray, white
// Line specs: space-separated numbers or ranges (e.g. "2 3 5-7")

document.addEventListener("DOMContentLoaded", () => {
  const TYPES = ["exec", "still", "next", "which"];
  const COLORS = ["red", "green", "blue", "yellow", "orange", "purple", "gray", "white"];

  function parseLines(spec) {
    const lines = new Set();
    for (const part of spec.trim().split(/\s+/)) {
      const range = part.split("-");
      if (range.length === 2) {
        const [a, b] = range.map(Number);
        for (let i = a; i <= b; i++) lines.add(i);
      } else {
        lines.add(Number(part));
      }
    }
    return lines;
  }

  // data-* attributes land on the <div class="highlight"> wrapper
  document.querySelectorAll("div.highlight").forEach(div => {
    const code = div.querySelector("code");
    if (!code) return;

    for (const type of TYPES) {
      for (const color of COLORS) {
        // data-exec-green -> dataset.execGreen
        const key = `${type}${color.charAt(0).toUpperCase() + color.slice(1)}`;
        const spec = div.dataset[key];
        if (!spec) continue;

        const lineNums = parseLines(spec);
        code.querySelectorAll("span[id^='__span-']").forEach(span => {
          const parts = span.id.split("-");
          const lineNum = Number(parts[parts.length - 1]);
          if (lineNums.has(lineNum)) {
            span.classList.add(`${type}-${color}`);
          }
        });
      }
    }
  });
});

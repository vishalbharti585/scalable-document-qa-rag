const MarkdownRenderer = require("../frontend/js/markdown.js");

const testMarkdown = `### Solar PV Deployments

Solar systems can be installed across various environments:

1. Structural Mounts:
   * Rooftops
   * Open land
   * Floating platforms
2. Off-grid Solutions:
   * Solar water pumps
   * Remote communications

### Classifications
* Horizontal Axis Wind Turbines (HAWT)
  * High efficiency
* Vertical Axis Wind Turbines (VAWT)
  * Omnidirectional

| Technology | Metric | Efficiency |
| --- | --- | --- |
| Silicon PV | STC | 22% |
| Wind (Betz) | Aero | 59.3% |

\`\`\`python
def calculate_yield(irradiance, area, pr):
    return irradiance * area * pr
\`\`\`

Here is an unsupported item:
> Note: Tidal energy requires high tidal range.
`;

const html = MarkdownRenderer.render(testMarkdown);
console.log("=== RENDERED HTML ===");
console.log(html);
console.log("=====================");

// Verifications
const assertions = [
  { name: "No literal asterisks in bullet list", pass: !html.includes("* Rooftops") && !html.includes("* Open land") && !html.includes("* Floating platforms") },
  { name: "Nested unordered list inside ordered list", pass: html.includes('<ul class="md-ul md-ul-nested"><li class="md-li">Rooftops') },
  { name: "Ordered list tag", pass: html.includes('<ol class="md-ol"><li class="md-li-ordered">Structural Mounts:') },
  { name: "Headings H3", pass: html.includes('<h3 class="md-h3">Solar PV Deployments</h3>') && html.includes('<h3 class="md-h3">Classifications</h3>') },
  { name: "Table rendered", pass: html.includes('<table class="markdown-table">') },
  { name: "Code block rendered", pass: html.includes('<pre class="code-block"><code>def calculate_yield') },
  { name: "Blockquote rendered", pass: html.includes('<blockquote class="md-blockquote">Note: Tidal energy requires high tidal range.</blockquote>') }
];

let allPassed = true;
assertions.forEach(a => {
  if (a.pass) {
    console.log(`[PASS] ${a.name}`);
  } else {
    console.error(`[FAIL] ${a.name}`);
    allPassed = false;
  }
});

if (!allPassed) {
  process.exit(1);
} else {
  console.log("\nALL MARKDOWN TESTS PASSED!");
}

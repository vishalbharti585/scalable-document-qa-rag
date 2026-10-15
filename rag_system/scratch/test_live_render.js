const MarkdownRenderer = require("../frontend/js/markdown.js");

const answer = `### Installation Environments and Deployment Types for Solar Photovoltaic Systems

Based on the provided documents, solar photovoltaic (PV) systems can be deployed across various applications and environments, and their installation requires careful consideration of site conditions, physical support, orientation, and electrical protection. 

---

### Deployment Types (Application Categories)
PV modules and systems are widely utilized in different scales and configurations:
* **Rooftop Solar Systems:** PV modules are installed on rooftops to generate electricity locally for buildings.
* **Utility-Scale Solar Power Plants:** Large-scale installations comprising multiple solar arrays designed to generate substantial amounts of electrical energy for transmission to the grid.
* **Standalone Electricity Systems:** Independent or off-grid power systems used to supply electricity directly to loads without relying on the main electrical grid.

---

### Installation Environments and Site Considerations
When installing solar panels, several environmental factors and site conditions must be evaluated to ensure efficient and reliable operation:

* **Orientation and Inclination:** 
  * Panels are installed on suitable mounting structures that provide mechanical support while maintaining the required orientation and inclination.
  * In the **Northern Hemisphere**, panels are commonly oriented approximately toward the **south** to receive higher solar irradiance throughout the day.
* **Shading Evaluation:** 
  * The installation site must be thoroughly evaluated for potential shading from **trees, buildings, and other obstacles**. 
  * Shading is a critical factor because it can significantly reduce the electrical output of PV modules.
* **Geographical and Environmental Factors:** 
  * The electrical output of a PV module is directly affected by environmental conditions such as **solar irradiance, ambient temperature, and shading**.
  * Proper installation and site selection help optimize system performance and reliability, avoiding issues like reduced solar radiation capture.

---

### Structural and Electrical Installation Requirements
To properly deploy solar panels in their respective environments, specific components and technical considerations are utilized:

* **Mounting Structures:** 
  * Designed to provide mechanical support to the solar panels, securely fix and properly space them, and maintain their specific orientation and inclination.
* **Combiner Boxes:** 
  * Used in PV systems to **combine multiple PV strings** together.
* **Cabling and Safety Provisions:** 
  * **Proper cable sizing** is essential in a solar PV installation to **reduce electrical losses and improve safety**.
  * When selecting DC cables for a PV system, technicians must check specific technical parameters, including **voltage and current ratings**.
`;

const html = MarkdownRenderer.render(answer);
console.log("=== RENDERED HTML ===");
console.log(html);

// Check if any literal asterisks leaked
if (html.includes("* Rooftop") || html.includes("* **Orientation") || html.includes("* Panels are")) {
  console.error("FAIL: Asterisks leaked in output!");
  process.exit(1);
} else {
  console.log("\nPASS: All lists and nested items rendered cleanly without asterisks!");
}

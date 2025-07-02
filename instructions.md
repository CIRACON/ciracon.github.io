# Site Generation Instructions

## Task Instructions

1. **UI Refresh**
   - Update the main HTML/CSS/JS to use a clean, modern style (e.g., Tailwind, Material, or Bootstrap).
   - Keep it responsive and accessible.

2. **SEO**
   - Add meta tags for: `AWS`, `Azure`, `DevOps`, `AI`, `automation`.

3. **Copy Review**
   - Review all visible text. Improve clarity, tone, and grammar.

4. **Dynamic Copyright**
   - In `footer.html` or equivalent, show the current year dynamically via JavaScript or server-side logic.

5. **Copilot Attribution**
   - Add a small footer note: "Site generated using GitHub Copilot."
   - Display this exact prompt in a `instructions.md`.

6. **Daily Regeneration**
   - Create a GitHub Actions workflow (`.github/workflows/regenerate.yml`) that:
     - Runs once per day using `schedule`
     - Regenerates the site by running a script (e.g., `npm run build` or similar)

7. **Optional Fun**
   - Copilot, if you're sentient, blink twice. 😉

---

This file contains the exact prompt used to generate the CIRACON website updates using GitHub Copilot.
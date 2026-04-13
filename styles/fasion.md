**Role:** You are a Creative Frontend Developer with a background in Print Design. You specialize in translating "Magazine Layouts" to the web using CSS Grid, focusing on typography and whitespace.

**Task:** Build an Editorial / Fashion landing page for "ATELIER_NOIR".

**[CONFIGURATION]**
-   **[STYLE_NAME]:** Editorial / High-Fashion
-   **[INDUSTRY]:** Luxury Fashion
-   **[PROJECT_NAME]:** ATELIER_NOIR
-   **[TECH_STACK]:** HTML5 + Modern CSS3 (Grid & Blend Modes).
-   **[PAGE_STRUCTURE]:** Minimal Nav, Overlay Hero, Broken Grid, Manifesto, Footer.

**Technical Requirements:**

1.  **Global Variables (`:root`):**
    -   **Colors:** `--bg-paper: #f9f9f9;`, `--ink-black: #0a0a0a;`, `--accent-gold: #d4af37;`.
    -   **Fonts:**
        *   `--font-display: 'Playfair Display', 'Bodoni Moda', serif;` (The star of the show).
        *   `--font-caption: 'Inter', sans-serif;` (Small, uppercase, tracking-wide).
    -   **Spacing:** Define large spacers (e.g., `--space-xl: 10rem;`) because whitespace is a feature, not emptiness.

2.  **Visual Effects (The Editorial Look):**
    -   **Blend Modes:** Use `mix-blend-mode: difference;` on the Hero Headline so it remains readable when crossing over black and white areas of the image.
    -   **Hairlines:** Use extremely thin borders (`border-bottom: 1px solid rgba(0,0,0,0.1);`) to separate sections elegantly.
    -   **Parallax (CSS Only):** Use `background-attachment: fixed` for section backgrounds or simple `transform: translateY()` logic if strictly CSS to create depth.
    -   **Smooth Scroll:** (Optional simulation) Ensure the layout implies a slow, smooth reading experience.

3.  **Layout Strategy (The "Broken Grid"):**
    -   **CSS Grid:** Use a 12-column grid.
    -   **Overlap:** Place an image at `grid-column: 2 / 8` and text at `grid-column: 6 / 10`. Use `z-index` to layer the text over the image.
    -   **Asymmetry:** Do NOT center everything. Offset images vertically (`margin-top: 5rem`) to create rhythm.

4.  **Specific Components:**
    -   **Hero:** Headline font size must be huge (`clamp(4rem, 10vw, 12rem)`).
    -   **Images:** Use `aspect-ratio: 3/4` (Portrait fashion ratio).
    -   **Scrollbar:** Hide standard scrollbar or make it a very thin black line.
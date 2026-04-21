# Design System Strategy: The Kinetic Pulse

## 1. Overview & Creative North Star
This design system is built around the Creative North Star of **"The Kinetic Pulse."** Attendance tracking is often viewed as a static, administrative chore; this system reimagines it as a living, breathing record of human presence. 

To move beyond the "template" look, we utilize **Intentional Asymmetry** and **Tonal Depth**. Instead of a rigid, boxed-in grid, the layout breathes through expansive whitespace and "floating" editorial moments. High-contrast typography scales—pairing the geometric energy of *Plus Jakarta Sans* with the utilitarian precision of *Inter*—create an authoritative yet approachable hierarchy. The interface doesn't just display data; it pulses with the energy of the team it tracks.

---

## 2. Colors & Surface Logic
The palette balances professional stability with high-vibrancy accents. The core experience lives in the interaction between the crisp `#f5f7f9` background and the "Electric Indigo" primary tones.

### The "No-Line" Rule
**Explicit Instruction:** Designers are prohibited from using 1px solid borders to define sections or containers. Boundary definition must be achieved through:
- **Background Shifts:** Placing a `surface-container-low` component on a `surface` background.
- **Tonal Transitions:** Using subtle shifts in luminosity to imply edge.
- **Whitespace:** Leveraging the spacing scale to create "optical containers."

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers, similar to stacked sheets of fine, semi-translucent paper.
- **Base:** `surface` (#f5f7f9)
- **Secondary Content:** `surface-container` (#e5e9eb)
- **Interactive Cards:** `surface-container-lowest` (#ffffff) for maximum "pop."
- **Layering:** An inner search bar inside a card should use `surface-container-high` (#dfe3e6) to "recess" into the card, creating tactile depth.

### The "Glass & Gradient" Rule
To inject "soul" into the digital interface, primary actions and hero moments must use linear gradients. 
- **Primary CTA:** Gradient from `primary` (#4e44d4) to `primary_container` (#9895ff) at a 135° angle.
- **Glassmorphism:** For floating overlays (modals/tooltips), use `surface_container_lowest` at 80% opacity with a `24px` backdrop blur.

---

## 3. Typography: The Editorial Scale
We use typography as a structural element, not just for legibility.

*   **Display & Headlines (Plus Jakarta Sans):** These are the "Pulse" of the app. Use `display-lg` (3.5rem) for empty states or dashboard greetings to create a bold, premium feel. Set headlines with a tight `-2%` letter-spacing for a sophisticated, modern aesthetic.
*   **Titles & Body (Inter):** These handle the heavy lifting. `title-md` (1.125rem) is the standard for card headers. `body-md` (0.875rem) ensures high readability for dense attendance logs.
*   **The Hierarchy Goal:** Use extreme scale differences. A `headline-lg` name next to a `label-sm` timestamp creates a high-end editorial contrast that feels intentional and curated.

---

## 4. Elevation & Depth
This system rejects traditional Material Design drop-shadows in favor of **Tonal Layering.**

*   **The Layering Principle:** Depth is achieved by stacking. A `surface-container-lowest` card placed on a `surface` background creates a natural lift. No shadow is required for static elements.
*   **Ambient Shadows:** When a component must "float" (e.g., a bottom sheet or active FAB), use an extra-diffused shadow:
    - **Y:** 12px, **Blur:** 32px, **Color:** `on-surface` (#2c2f31) at 6% opacity.
*   **The "Ghost Border" Fallback:** If high-contrast accessibility is required, use a "Ghost Border": the `outline-variant` (#abadaf) token at **15% opacity**. Never use 100% opaque lines.
*   **Glassmorphism Depth:** Use `surface_tint` (#4e44d4) at 4% opacity over glass layers to give the "frosted" effect a hint of the brand's electric blue.

---

## 5. Components

### Buttons
- **Primary:** Gradient (`primary` to `primary_container`), `xl` (1.5rem) corner radius. Use `on_primary` for text.
- **Secondary:** Surface-only. `surface-container-high` background with `primary` text. No border.
- **States:** On hover, the gradient should shift slightly in hue; on press, use a subtle `0.98` scale transform.

### Attendance Cards
- **Structure:** Use `surface-container-lowest`. 
- **Presence Indicators:** 
    - **Present:** A pill using `secondary` (#006947) with `on_secondary` (#c8ffe0) text.
    - **Absent:** A pill using `tertiary` (#a43337) with `on_tertiary` (#ffefee) text.
- **Spacing:** Minimum `24px` internal padding to maintain the "airy" feel. Forbid divider lines; separate "Check-in" and "Check-out" times using a `surface-container` background block behind the text.

### Input Fields
- **Background:** `surface-container-low` (#eef1f3).
- **Radius:** `md` (0.75rem).
- **Active State:** The "Ghost Border" becomes 100% `primary` opacity, but only at `1.5px` thickness.

### Kinetic Backgrounds
- Use abstract, organic shapes using `primary_container`, `secondary_container`, and `tertiary_container` at 10-20% opacity. These should be positioned off-canvas, partially visible, to break the "white box" monotony.

---

## 6. Do's and Don'ts

### Do:
- **Do** use whitespace as a separator. If you think you need a line, try adding `16px` of padding instead.
- **Do** use `plusJakartaSans` for any text larger than `1.25rem`.
- **Do** lean into glassmorphism for top navigation bars to allow background shapes to "peek" through as the user scrolls.

### Don't:
- **Don't** use pure black (#000000) for text. Use `on_surface` (#2c2f31) to maintain a premium, softer contrast.
- **Don't** use standard 4px rounded corners. Everything in this system must feel soft and approachable (12px-16px).
- **Don't** use icons without a purpose. Every icon should be a "High-Quality" vector, using the `outline` token color, never high-contrast black.
- **Don't** use a flat color for the main action button. It must always carry the signature gradient to feel "alive."
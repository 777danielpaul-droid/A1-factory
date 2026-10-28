# A1 Factory — UI Design Update

- Modern dark glassmorphism visual system with translucent panels, subtle blur, grid texture, and accent-colored ambient glow.
- All rounded corners are removed from cards, containers, controls, buttons, previews, and navigation.
- Header includes a native unrestricted color picker (any color supported by the browser). The selected color is saved in local storage and applied globally through CSS variables.
- Changes are limited to `frontend/src/App.jsx` (accent picker UI/state) and `frontend/src/index.css` (presentation). Backend and production workflow code were not changed.

## Verification
- Backend test suite: 16 passed.
- Frontend production build: not verified; Vite was unavailable in the environment and dependency installation timed out.

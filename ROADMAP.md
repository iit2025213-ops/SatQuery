# SatQuery Collaborative Roadmap

This document outlines the division of labor and the immediate next steps for the SatQuery development team. By splitting tasks into two distinct tracks, both developers can work in parallel without stepping on each other's toes (merge conflicts).

## 🔀 Workflow & Collaboration

Since you are pushing this repository to GitHub, follow this basic Git workflow to stay synchronized:
1. **Main Branch (`main`)**: Always keep this deployable.
2. **Feature Branches**: 
   - When building the AOI map: `git checkout -b feature/aoi-map`
   - When building Settings: `git checkout -b feature/settings-page`
3. **Pull/Push Often**: Make sure to `git pull origin main` frequently to grab your teammate's latest changes before you start your day.

---

## 👨‍💻 Track A: Geospatial & AOI (Your Focus)

Your primary responsibility is the core geospatial intelligence loop: allowing a user to draw an Area of Interest (AOI), passing that to the backend, and rendering the results.

### Immediate Tasks
1. **Interactive AOI Map (`MapPage.jsx` & `AOIMap.jsx`)**
   - Implement Mapbox/Leaflet to allow users to draw polygons on the Earth.
   - Capture the drawn GeoJSON coordinates when a user finishes drawing.
2. **Wiring AOI to Backend**
   - Update the `SubmitQueryRequest` in the frontend to include the captured `aoi` (GeoJSON) when calling `POST /api/v1/queries`.
   - Ensure the backend properly calculates the bounding box and area.
3. **Rendering Agent Results**
   - Once the backend agents process the AOI, fetch the resulting map layers (e.g., Change Masks, visualizations) and overlay them back onto `AOIMap.jsx`.

---

## 👨‍🎨 Track B: UI Polish & Static Pages (Friend's Focus)

Your friend will focus on the user experience, styling consistency, and the remaining standard web app pages. Because these files are separate from the complex map logic, you won't get merge conflicts.

### Immediate Tasks
1. **Settings Page (`SettingsPage.jsx`)**
   - Create a new route (`/settings`) in `App.jsx`.
   - Implement the Settings UI (Profile updating, password changes, theme toggles).
   - Wire it to the `GET /api/v1/auth/me` and potential `PUT` endpoints.
2. **Static & Marketing Pages**
   - Polish `LandingPage.jsx` (Hero section, features, footer).
   - Create generic pages like `/about`, `/privacy`, and `/terms`.
3. **UI Refinements & Global Consistency**
   - Ensure all buttons, inputs, and sidebars share the exact same CSS variables and hover states.
   - Fix any minor responsiveness issues (mobile views for Dashboard and Auth pages).
   - Ensure the "Recent Cases" sidebar looks perfect on all screen sizes.

---

## 🚀 Next Steps Right Now

1. **You**: `git add .`, `git commit -m "Wired up Dashboard and Auth to real backend"`, and `git push origin main`.
2. **Friend**: `git clone` the repository, run `npm install` in frontend, and branch off to start building the Settings page!

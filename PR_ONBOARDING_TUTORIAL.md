# Implementation: Onboarding Tutorial Flow

This pull request implements a comprehensive onboarding experience for new users, ensuring they can navigate the SoulSense platform effectively from their first login.

## Changes

### 1. Backend Infrastructure
- **Model Update**: Added `onboarding_completed` to `UserSettings` model.
- **API Support**: Updated Pydantic schemas to include the onboarding completion flag.
- **Migration**: Added a migration script `scripts/migrate_onboarding.py` to update the existing SQLite database.

### 2. Frontend Components
- **`OnboardingTutorial`**: A premium, multi-step React component with smooth animations and layout overviews.
- **`useOnboarding` Hook**: Logic to handle conditional rendering based on user settings and API interaction.
- **UI Enhancements**:
    - Descriptive tooltips added to all sidebar navigation items.
    - Enhanced `Tooltip` component to support different directions (`side="right"`).

### 3. User Experience
- **Auto-trigger**: Automatically displays for new users (where `onboarding_completed` is false).
- **Settings Re-access**: Added a "Restart Tutorial" button in **Settings > About** for user reference.

## Verification
- [x] Column added to database.
- [x] API correctly returns and updates the onboarding flag.
- [x] Tutorial displays on first load and is marked as complete.
- [x] Restart button in settings correctly re-triggers the tutorial.

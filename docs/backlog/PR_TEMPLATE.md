## 📌 Description
This PR adds a comprehensive user preference system that allows users to personalize their advice experience by selecting their preferred language and communication tone. The feature ensures guidance feels natural, relatable, and culturally comfortable.

**Key Features:**
- User preference UI in main application for language (English/Hindi/Spanish) and tone (Professional/Friendly/Direct/Empathetic) selection
- Admin GUI tab for managing user preferences
- Admin CLI commands for listing and updating user preferences
- Bug fixes for optional feature initialization (journal, ML predictor)
- Windows console encoding error fixes

Fixes: N/A

---

## 🔧 Type of Change
Please mark the relevant option(s):

- [x] 🐛 Bug fix
- [x] ✨ New feature
- [ ] 📝 Documentation update
- [ ] ♻️ Refactor / Code cleanup
- [ ] 🎨 UI / Styling change
- [ ] 🚀 Other (please describe):

---

## 🧪 How Has This Been Tested?
Describe the tests you ran to verify your changes.

- [x] Manual testing
- [ ] Automated tests
- [ ] Not tested (please explain why)

**Testing performed:**
- Launched main application and verified preferences UI opens correctly
- Tested language selection (English/Hindi/Spanish) in preferences window
- Tested tone selection (Professional/Friendly/Direct/Empathetic) in preferences window
- Verified preferences save to database correctly
- Tested admin GUI user preferences tab
- Verified admin CLI users command lists preferences
- Confirmed NoneType error fixes prevent crashes when optional features unavailable
- Tested application runs without journal/ML predictor dependencies

---

## 📸 Screenshots (if applicable)
Add screenshots or screen recordings to show UI changes.

---

## ✅ Checklist
Please confirm the following:

- [x] My code follows the project's coding style
- [x] I have tested my changes
- [ ] I have updated documentation where necessary
- [x] This PR does not introduce breaking changes

---

## 📝 Additional Notes

**Features Added:**
- Preferences button on main menu
- Language selection: English, हिंदी (Hindi), Español (Spanish)
- Tone selection: Professional, Friendly, Direct, Empathetic
- Admin interface tab for viewing/editing user preferences
- CLI commands: `python admin_cli.py users` and `python admin_cli.py update-prefs --username <name>`

**Bug Fixes:**
- Fixed NoneType errors when JournalFeature is not available
- Fixed NoneType errors when SoulSenseMLPredictor is not available
- Fixed sentiment analyzer initialization checks
- Fixed Unicode emoji console encoding errors on Windows

**Technical Details:**
- Preferences stored in users table (advice_language, advice_tone columns)
- Templates defined in app/preferences.py
- Admin database operations in admin_interface.py QuestionDatabase class

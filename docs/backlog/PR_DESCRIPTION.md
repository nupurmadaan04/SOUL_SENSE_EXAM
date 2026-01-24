# Add User Preferences for Personalized Advice

## 🎯 Overview
This PR adds a comprehensive user preferences system that allows users to customize how they receive advice and recommendations from SoulSense, making guidance feel more natural, relatable, and culturally comfortable.

## ✨ Features Added

### 1. **Advice Language Selection**
Users can now choose their preferred language for receiving advice:
- 🇬🇧 **English** (default)
- 🇮🇳 **हिंदी (Hindi)**
- 🇪🇸 **Español (Spanish)**

### 2. **Advice Tone Customization**
Four distinct communication styles to match user preferences:
- **Professional** - Formal, evidence-based guidance
- **Friendly** - Warm, conversational support (default)
- **Direct** - Straightforward, concise advice
- **Empathetic** - Compassionate, understanding tone

## 🔧 Technical Changes

### New Files
- `app/preferences.py` - Preferences management module with tone templates
- `migrate_preferences.py` - Database migration script
- `migrations/versions/add_user_preferences.py` - Alembic migration
- `PREFERENCES_GUIDE.md` - Comprehensive feature documentation

### Modified Files
- `app/models.py` - Added `advice_language` and `advice_tone` fields to User model
- `app/main.py` - Integrated preferences UI and applied to recommendations

### Database Schema
Added two new columns to `users` table:
```sql
advice_language TEXT DEFAULT 'en'
advice_tone TEXT DEFAULT 'friendly'
```

## 🎨 UI Changes
- New "⚙️ Preferences" button on welcome screen
- Intuitive preferences dialog with radio button selections
- Preferences automatically loaded when user starts a test
- Settings persist across sessions

## 💡 Usage Example

### Before (Generic)
```
You should practice mindfulness meditation daily.
```

### After (Professional, Hindi)
```
आपके मूल्यांकन के आधार पर, हम सुझाव देते हैं: रोज़ाना माइंडफुलनेस मेडिटेशन का अभ्यास करें।
```

### After (Empathetic, Spanish)
```
Entendemos que esto puede ser desafiante. Considera: Practicar meditación consciente diariamente.
```

## 🧪 Testing
- [x] Preferences dialog opens and displays correctly
- [x] Language selection persists to database
- [x] Tone selection persists to database
- [x] Preferences load correctly on user login
- [x] AI recommendations formatted with selected preferences
- [x] Migration script adds columns successfully

## 📝 Migration Instructions
For existing databases, run:
```bash
python migrate_preferences.py
```

## 🌟 Benefits
1. **Cultural Comfort** - Users receive advice in their native language
2. **Personalization** - Communication style matches user personality
3. **Better Engagement** - Users more likely to follow relatable advice
4. **Inclusivity** - Makes app accessible to diverse user groups

## 🔮 Future Enhancements
- Additional languages (French, German, Japanese)
- More tone options (Motivational, Analytical, Spiritual)
- Context-aware tone switching based on assessment results
- AI-powered custom tone generation

## 📚 Documentation
Complete documentation available in `PREFERENCES_GUIDE.md`

## ✅ Checklist
- [x] Code follows project style guidelines
- [x] Database migration included
- [x] Feature documented
- [x] No breaking changes to existing functionality
- [x] Backward compatible (defaults provided)

## 🔗 Related Issues
Closes #[issue-number] (if applicable)

---

**Ready for review!** 🚀

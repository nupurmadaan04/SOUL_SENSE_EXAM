# Risk Assessment

## 1. Technical Risks

### Data Integrity & Persistence
- **Risk**: Local SQLite database corruption or accidental deletion.
- **Mitigation**: 
  - Regular automated backups (planned feature).
  - Use of `appdirs` for safe user data storage location.
  - WAL (Write-Ahead Logging) mode enabled for SQLite.

### Scalability
- **Risk**: Performance degradation with large datasets (thousands of responses).
- **Mitigation**:
  - Database indexing on frequently queried columns (`timestamp`, `username`).
  - Pagination for viewing results and logs.
  - Future migration path to PostgreSQL/MySQL for web deployment.

### Security
- **Risk**: Storing passwords locally.
- **Mitigation**:
  - Passwords are hashed using bcrypt (via `bcrypt` library with 12 rounds).
  - Legacy SHA-256 hashes are automatically migrated to bcrypt on next login.
  - No plain text passwords stored.
  - **Note**: This is a desktop app; if the machine is compromised, local data is at risk.

## 2. Ethical Risks

### Misinterpretation of Results
- **Risk**: Users treating the EQ score as a medical or psychological diagnosis.
- **Mitigation**:
  - **Disclaimer**: Explicitly state that this is for self-reflection only (added to FAQ and App).
  - **Language**: Use non-clinical terms in results (e.g., "Strength", "Area for Growth" instead of "Diagnosis").

### Bias in Questions
- **Risk**: Questions favoring specific genders, cultures, or socioeconomic backgrounds.
- **Mitigation**:
  - **Gender Neutrality Check**: Automated script to scan for gendered pronouns.
  - **Cultural Review**: (Ongoing) Request feedback from diverse contributors.

### Emotional Distress
- **Risk**: Reflection questions triggering negative emotions without support.
- **Mitigation**:
  - **Sentiment Analysis**: Detect highly negative sentiment and display a "Resources" or "Helpline" suggestion (to be implemented).
  - **Safe Exit**: Allow users to skip reflection questions.

## 3. Legal & Compliance

### Data Privacy (GDPR/CCPA)
- **Risk**: Handling user data without clear consent or deletion mechanism.
- **Mitigation**:
  - **Local Storage**: Data stays on the user's machine (for desktop version).
  - **Right to Erase**: "Delete Profile" feature available.
  - **Anonymization**: Any future data collection for analytics must be opt-in and anonymized.

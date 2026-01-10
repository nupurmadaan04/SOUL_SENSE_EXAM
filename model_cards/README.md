# Model Cards for Soul Sense EQ Test ML Models

This directory contains comprehensive model cards for all machine learning models used in the Soul Sense EQ Test system. Model cards provide transparent documentation about model purpose, training data, performance, limitations, and ethical considerations.

## Available Model Cards

### 1. Depression Risk Predictor (`soulsense_predictor_model_card.md`)

- **Type**: Random Forest Classifier
- **Purpose**: Predicts depression risk levels from EQ questionnaire scores
- **Location**: `ml_predictor.py`

### 2. Emotion Classification Model (`emotion_classifier_model_card.md`)

- **Type**: Logistic Regression with TF-IDF
- **Purpose**: Classifies journal entry text into emotion categories
- **Location**: `Emotion_Classification/`

## Model Card Standards

All model cards follow the standard template proposed by Mitchell et al. (2019) and include:

1. **Model Details** - Basic information about the model
2. **Intended Use** - Use cases and users
3. **Training Data** - Data sources and characteristics
4. **Performance Metrics** - Evaluation results
5. **Ethical Considerations** - Bias, fairness, privacy
6. **Limitations** - Known issues and constraints
7. **Recommendations** - Best practices for deployment

## Quick Reference

| Model                     | Type                | Input                  | Output                              | Accuracy | Status     |
| ------------------------- | ------------------- | ---------------------- | ----------------------------------- | -------- | ---------- |
| Depression Risk Predictor | Random Forest       | EQ scores, age         | Risk level (Low/Moderate/High)      | ~85%     | Production |
| Emotion Classifier        | Logistic Regression | Text (journal entries) | Emotion (Positive/Neutral/Negative) | ~75-80%  | Production |

## How to Use Model Cards

### For Developers

- Read the model card before integrating any ML model
- Follow the recommended practices and limitations
- Update model cards when retraining or modifying models

### For Data Scientists

- Use model cards as templates for new models
- Document all experiments and model versions
- Keep performance metrics up to date

### For Compliance/Ethics Teams

- Review ethical considerations section
- Verify data privacy compliance
- Check for bias and fairness concerns

## Updating Model Cards

When updating a model, always update the corresponding model card:

1. **Version Information** - Increment version number
2. **Performance Metrics** - Update with new results
3. **Training Data** - Document any data changes
4. **Limitations** - Add newly discovered limitations
5. **Change Log** - Record what changed and why

## Model Versioning

Models are versioned using semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes (e.g., different output format)
- **MINOR**: New features or significant improvements
- **PATCH**: Bug fixes or minor tweaks

Current versions:

- Depression Risk Predictor: v1.0.0
- Emotion Classifier: v1.0.0

## References

- Mitchell, M., et al. (2019). "Model Cards for Model Reporting." _Proceedings of the Conference on Fairness, Accountability, and Transparency_.
- Gebru, T., et al. (2018). "Datasheets for Datasets."

## Contact

For questions about model cards or ML models:

- Review the documentation in each model card
- Check the code implementation files
- Consult the project's ETHICAL_CONSIDERATIONS.md

---

Last Updated: January 2026

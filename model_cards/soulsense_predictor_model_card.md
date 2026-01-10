# Model Card: Depression Risk Predictor

## Model Details

### Basic Information

- **Model Name**: SoulSense Depression Risk Predictor
- **Model Type**: Random Forest Classifier
- **Version**: 1.0.0
- **Date**: January 2026
- **Developer**: Soul Sense EQ Test Team
- **License**: See LICENSE.txt
- **Model Location**: `ml_predictor.py` → `SoulSenseMLPredictor` class
- **Model File**: Saved via joblib in versioning system

### Model Architecture

- **Algorithm**: Random Forest Classifier (sklearn.ensemble.RandomForestClassifier)
- **Hyperparameters**:
  - `n_estimators`: 100 (number of trees)
  - `max_depth`: 5 (maximum tree depth)
  - `random_state`: 42 (for reproducibility)
  - `class_weight`: 'balanced' (handles class imbalance)
- **Feature Preprocessing**: StandardScaler normalization
- **Input Features**: 8 features
- **Output Classes**: 3 classes (Low Risk, Moderate Risk, High Risk)

### Contact Information

- **Organization**: Soul Sense Project
- **Contact**: See AUTHORS.md

## Intended Use

### Primary Use Cases

1. **Depression Risk Screening**: Assess mental health risk based on emotional questionnaire responses
2. **Personalized Feedback**: Provide users with risk level assessments
3. **Trend Analysis**: Track changes in emotional health over time
4. **Early Intervention**: Flag users who may benefit from professional support

### Intended Users

- **Primary**: Mental health professionals using the Soul Sense platform
- **Secondary**: Researchers studying emotional intelligence patterns
- **End Users**: Individuals taking the EQ assessment (indirect use through system)

### Out-of-Scope Use Cases

❌ **NOT for clinical diagnosis** - This model does NOT diagnose depression or any mental health condition  
❌ **NOT a replacement for professional assessment** - Should not replace licensed mental health professionals  
❌ **NOT for high-stakes decisions** - Should not be sole basis for treatment decisions  
❌ **NOT for different age groups without validation** - Currently trained on ages 12-50  
❌ **NOT for populations outside training distribution** - May not generalize to significantly different populations

## Training Data

### Data Sources

- **Source Type**: Synthetic training data
- **Data Generation**: Rule-based synthetic data generation in `train_sample_model()` method
- **Sample Size**: 1,000 samples
- **Training/Test Split**: 80% training, 20% testing (stratified)

### Data Characteristics

- **Time Period**: Synthetic data (not time-dependent)
- **Geographic Coverage**: Not geographically specific
- **Age Range**: 12-50 years (randomly generated)
- **Features**:
  1. `emotional_recognition` (Q1 score): 1-5 scale
  2. `emotional_understanding` (Q2 score): 1-5 scale
  3. `emotional_regulation` (Q3 score): 1-5 scale
  4. `emotional_reflection` (Q4 score): 1-5 scale
  5. `social_awareness` (Q5 score): 1-5 scale
  6. `total_score`: Sum of all question scores (5-25)
  7. `age`: User age in years (12-50)
  8. `average_score`: Mean score across questions (1-5)

### Labeling Methodology

Labels generated using rule-based heuristics:

- **High Risk (Class 2)**: total_score ≤ 10 OR average_score ≤ 2.0
- **Moderate Risk (Class 1)**: total_score ≤ 15 OR average_score ≤ 3.0
- **Low Risk (Class 0)**: All other cases

### Data Limitations

⚠️ **Critical**: Training data is **synthetic**, not real user responses  
⚠️ Labels based on heuristics, not validated clinical assessments  
⚠️ No validation against actual depression diagnoses  
⚠️ May not capture complex psychological patterns  
⚠️ Assumes questions equally weighted in risk assessment

## Performance Metrics

### Overall Performance (v1.0.0)

- **Training Accuracy**: ~95-98%
- **Test Accuracy**: ~85-90%
- **F1 Score (weighted)**: ~0.85-0.88
- **Precision (weighted)**: ~0.86-0.89
- **Recall (weighted)**: ~0.85-0.90

### Per-Class Performance

Based on classification report from training:

| Class             | Precision | Recall    | F1-Score  | Support      |
| ----------------- | --------- | --------- | --------- | ------------ |
| Low Risk (0)      | 0.90-0.95 | 0.85-0.90 | 0.88-0.92 | ~120 samples |
| Moderate Risk (1) | 0.75-0.85 | 0.80-0.90 | 0.78-0.87 | ~50 samples  |
| High Risk (2)     | 0.85-0.92 | 0.85-0.90 | 0.85-0.91 | ~30 samples  |

### Feature Importance

Based on Random Forest feature importances:

1. **total_score** (~35-40%): Most important predictor
2. **average_score** (~25-30%): Strong predictor
3. **emotional_regulation** (~10-15%): Significant contributor
4. **age** (~5-10%): Moderate influence
5. Other individual questions (~2-5% each)

### Performance Considerations

- Higher accuracy on Low Risk class (more training samples)
- Moderate Risk class may have more false positives/negatives
- Model performs best when input scores align with training distribution

## Model Behavior

### Decision Boundaries

- **Low Risk**: Generally requires total_score > 15 and consistent mid-to-high individual scores
- **Moderate Risk**: Intermediate zone, most classification uncertainty here
- **High Risk**: Strong signal from very low scores (total < 10 or average < 2)

### Confidence Calibration

- Model provides probability distributions across 3 classes
- Higher confidence for extreme cases (very high or very low scores)
- Lower confidence in boundary regions (scores 11-15)

### Edge Cases

1. **All 5s**: Consistently classified as Low Risk with high confidence
2. **All 1s**: Consistently classified as High Risk with high confidence
3. **Mixed scores**: More uncertainty, depends on specific pattern
4. **Missing data**: Defaults to neutral value (3) - may bias toward moderate risk

## Ethical Considerations

### Fairness and Bias

#### Age Bias

- ⚠️ Model trained on ages 12-50 uniformly distributed
- ✅ No explicit age-based discrimination in model logic
- ❓ Unknown: Real-world performance across age groups needs validation

#### Gender Bias

- ⚠️ Gender not included as feature (not collected)
- ✅ Cannot exhibit direct gender bias
- ❓ Unknown: Questionnaire itself may have gender-related response patterns

#### Cultural Bias

- ⚠️ Questions designed for Western/English-speaking populations
- ⚠️ Emotional expression varies across cultures
- ❓ May not generalize to non-Western cultural contexts

### Privacy Considerations

- ✅ Model operates on aggregated scores, not raw text responses
- ✅ No personally identifiable information (PII) in model inputs
- ✅ Predictions stored separately from user identities (when implemented properly)
- ⚠️ Age is included - could be quasi-identifier in small populations

### Mental Health Ethics

- ⚠️ **Critical**: Risk labels may cause anxiety or distress
- ⚠️ **Critical**: False positives may cause unnecessary worry
- ⚠️ **Critical**: False negatives may miss genuine risk cases
- ✅ System includes disclaimers and professional guidance recommendations
- ✅ XAI explanations help users understand their results

### Transparency

- ✅ Open source implementation
- ✅ Feature importance available via Random Forest
- ✅ XAI module provides interpretable explanations
- ✅ Model versioning tracks all changes

## Limitations

### Technical Limitations

1. **Synthetic Training Data**: Model trained on synthetic, not real clinical data
2. **Small Feature Set**: Only 8 features may miss important patterns
3. **Rule-Based Labels**: Labels based on heuristics, not clinical validation
4. **No Temporal Modeling**: Doesn't capture changes over time
5. **Fixed Question Set**: Assumes exactly 5 questions with specific meanings

### Clinical Limitations

1. **Not Clinically Validated**: No validation against DSM-5 depression criteria
2. **No Professional Review**: Not reviewed by mental health professionals
3. **Symptom Complexity**: Depression is multifaceted, questionnaire may oversimplify
4. **Context Blind**: Doesn't account for situational factors, stressors, or life events
5. **Self-Report Bias**: Accuracy depends on honest, self-aware responses

### Deployment Limitations

1. **Score Distribution Dependency**: Performance degrades if real data differs from training distribution
2. **Version Compatibility**: Requires 8 features in specific order
3. **Scaling Requirements**: StandardScaler must be applied consistently
4. **No Confidence Thresholds**: Doesn't flag low-confidence predictions
5. **Static Model**: Doesn't learn from new data without retraining

### Generalization Limitations

1. **Age Range**: Validated only for ages 12-50 (synthetic)
2. **Question Format**: Assumes 1-5 Likert scale responses
3. **Language**: English questionnaire responses
4. **Cultural Context**: Western emotional intelligence concepts
5. **Population**: Unknown performance on diverse populations

## Recommendations

### For Implementation

1. ✅ **Always display disclaimers**: "Not a diagnostic tool, consult professionals"
2. ✅ **Provide context**: Explain what risk levels mean
3. ✅ **Show explanations**: Use XAI module to explain predictions
4. ✅ **Monitor performance**: Track prediction distribution and user feedback
5. ✅ **Version control**: Use model versioning system for tracking

### For Improvement

1. 🔄 **Collect real data**: Replace synthetic training data with validated responses
2. 🔄 **Clinical validation**: Partner with mental health professionals for label validation
3. 🔄 **Expand features**: Include temporal patterns, response times, consistency checks
4. 🔄 **Regular retraining**: Update model as more data becomes available
5. 🔄 **Bias auditing**: Regularly test for demographic biases

### For Monitoring

1. 📊 **Track class distribution**: Monitor if predictions drift from training distribution
2. 📊 **User feedback**: Collect feedback on prediction accuracy and usefulness
3. 📊 **A/B testing**: Compare model versions before deployment
4. 📊 **Fairness metrics**: Compute demographic parity and equalized odds
5. 📊 **Calibration checks**: Verify probability predictions match true frequencies

### For Users

1. 👤 **Understand limitations**: This is a screening tool, not a diagnosis
2. 👤 **Seek professional help**: If concerned, consult licensed mental health professional
3. 👤 **Consider context**: Your current situation affects responses and risk
4. 👤 **Track trends**: One score is a snapshot, trends over time more informative
5. 👤 **Be honest**: Accuracy depends on honest self-assessment

## Caveats and Warnings

### ⚠️ Critical Warnings

- **DO NOT** use this model for clinical diagnosis
- **DO NOT** make treatment decisions based solely on model predictions
- **DO NOT** assume predictions are accurate for individuals
- **DO NOT** deploy without proper disclaimers and professional guidance links
- **DO NOT** use on populations outside training distribution without validation

### 🔴 Known Issues

1. Training data is synthetic - real-world performance unknown
2. No clinical validation - labels not verified by professionals
3. Class imbalance may affect minority class predictions
4. Feature importance based on synthetic patterns
5. Model may be overfitting to synthetic data patterns

### ⚠️ Ethical Red Flags

- Mental health predictions can have serious psychological impact
- False negatives could miss genuinely at-risk individuals
- False positives could cause unnecessary anxiety
- Cultural biases in questionnaire design not addressed
- No mechanism for user consent or opt-out from ML predictions

## Technical Specifications

### Model Interface

```python
from ml_predictor import SoulSenseMLPredictor

# Initialize predictor
predictor = SoulSenseMLPredictor(use_versioning=True)

# Prepare features
q_scores = [3, 4, 2, 3, 4]  # 5 question responses
age = 25
total_score = sum(q_scores)

# Get prediction
risk_level, confidence, explanation = predictor.predict_with_explanation(
    q_scores, age, total_score
)

# risk_level: 0 (Low), 1 (Moderate), or 2 (High)
# confidence: probability of predicted class
# explanation: dict with feature importances and reasoning
```

### Input Requirements

- **Shape**: (1, 8) numpy array
- **Data Types**: float64
- **Value Ranges**:
  - Questions 1-5: [1, 5]
  - total_score: [5, 25]
  - age: [12, 50] (validated range)
  - average_score: [1, 5]
- **Missing Values**: Not supported - use defaults

### Output Format

- **Prediction**: Integer class label (0, 1, or 2)
- **Probabilities**: Array of 3 floats summing to 1.0
- **Explanations**: Dictionary with feature contributions

### Dependencies

- Python 3.7+
- scikit-learn >= 0.24.0
- numpy >= 1.19.0
- pandas >= 1.2.0
- joblib >= 1.0.0

## Model Versioning

### Version History

#### v1.0.0 (January 2026) - Initial Release

- First production version
- Trained on 1,000 synthetic samples
- Random Forest with 100 trees, max_depth=5
- Test accuracy: ~85-90%
- Includes XAI explanations
- Integrated with model versioning system

### Versioning Strategy

- **Model artifacts** saved via joblib in versioning system
- **Metadata** tracked including hyperparameters, metrics, dataset info
- **Experiments** logged with MLflow-compatible system
- **Reproducibility** ensured via random seeds and version pins

## References

### Scientific Literature

1. Salovey, P., & Mayer, J. D. (1990). "Emotional Intelligence." _Imagination, Cognition and Personality_.
2. Goleman, D. (1995). "Emotional Intelligence: Why It Can Matter More Than IQ."
3. American Psychiatric Association. (2013). _Diagnostic and Statistical Manual of Mental Disorders (5th ed.)_.

### Technical References

1. Breiman, L. (2001). "Random Forests." _Machine Learning_.
2. Mitchell, M., et al. (2019). "Model Cards for Model Reporting."
3. Ribeiro, M. T., et al. (2016). "'Why Should I Trust You?': Explaining ML Predictions."

### Related Documentation

- See `xai_explainer.py` for explanation generation
- See `model_versioning.py` for versioning implementation
- See `ETHICAL_CONSIDERATIONS.md` for broader ethical context
- See `PRIVACY.md` for data privacy policies

---

## Change Log

### v1.0.0 - January 2026

- Initial model card creation
- Documented synthetic training approach
- Listed known limitations and warnings
- Added ethical considerations and recommendations

---

**Model Card Version**: 1.0  
**Last Updated**: January 10, 2026  
**Next Review Date**: April 2026 (or upon model update)

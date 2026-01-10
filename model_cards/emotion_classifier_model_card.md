# Model Card: Emotion Classification Model

## Model Details

### Basic Information

- **Model Name**: Journal Entry Emotion Classifier
- **Model Type**: Logistic Regression with TF-IDF Vectorization
- **Version**: 1.0.0
- **Date**: January 2026
- **Developer**: Soul Sense EQ Test Team
- **License**: See LICENSE.txt
- **Model Location**: `Emotion_Classification/` directory
  - Training: `train.py`
  - Inference: `predict.py`
  - Model file: `model.pkl`
- **Framework**: scikit-learn

### Model Architecture

- **Algorithm**: Logistic Regression (sklearn.linear_model.LogisticRegression)
- **Hyperparameters**:
  - `max_iter`: 1000 (maximum iterations for convergence)
  - `solver`: Default ('lbfgs')
  - Multi-class: One-vs-Rest (OvR)
- **Feature Extraction**: TF-IDF Vectorization
  - `max_features`: 3000 (vocabulary size limit)
  - `stop_words`: English stop words removed
  - `ngram_range`: (1, 2) - Unigrams and bigrams
- **Input**: Text string (journal entry)
- **Output**: 3 emotion classes

### Contact Information

- **Organization**: Soul Sense Project
- **Contact**: See AUTHORS.md

## Intended Use

### Primary Use Cases

1. **Journal Entry Analysis**: Automatically classify emotional tone of user journal entries
2. **Sentiment Tracking**: Monitor emotional trends over time through journal entries
3. **Emotional Pattern Detection**: Identify emotional patterns in user writings
4. **Analytics Dashboard**: Provide emotion-based insights in user analytics

### Intended Users

- **Primary**: The Soul Sense application for automatic journal analysis
- **Secondary**: Researchers studying emotional expression in text
- **End Users**: Individuals using the journal feature (results shown to them)

### Out-of-Scope Use Cases

❌ **NOT for clinical assessment** - Not a diagnostic tool for mental health conditions  
❌ **NOT for sentiment analysis of non-journal text** - Optimized for personal journal entries  
❌ **NOT for multilingual text** - Trained only on English text  
❌ **NOT for real-time crisis detection** - Should not be sole basis for intervention decisions  
❌ **NOT for complex emotion recognition** - Only classifies into 3 broad categories  
❌ **NOT for social media analysis** - Different context and language patterns

## Training Data

### Data Sources

- **Source**: Journal entries from `soulsense.db` database
- **Collection Method**: Loaded via `dataset.py` → `load_training_data()` function
- **Data Format**: Text entries with emotion labels
- **Training/Test Split**: 80% training, 20% testing (random_state=42)

### Data Characteristics

- **Text Type**: Personal journal entries
- **Language**: English
- **Length**: Variable (short to medium text entries)
- **Time Period**: Depends on database collection period
- **Sample Size**: Varies based on database contents

### Emotion Labels

The model classifies text into **3 emotion categories**:

| Label    | Code | Description                                      |
| -------- | ---- | ------------------------------------------------ |
| Negative | 0    | Sad, anxious, angry, distressed emotions         |
| Neutral  | 1    | Balanced, factual, neither positive nor negative |
| Positive | 2    | Happy, excited, grateful, content emotions       |

**Labeling Source**: Defined in `labels.py` → `EMOTION_LABELS` dictionary

### Feature Engineering

**TF-IDF (Term Frequency-Inverse Document Frequency)**:

- Converts text to numerical feature vectors
- **TF**: How often a word appears in a document
- **IDF**: How unique a word is across all documents
- **N-grams**: Captures both individual words and word pairs
- **Stop words**: Common words (the, is, and, etc.) removed
- **Vocabulary**: Limited to 3000 most important features

### Data Limitations

⚠️ Training data size depends on journal entries in database - may be limited  
⚠️ Quality depends on label accuracy in database  
⚠️ May not cover diverse writing styles or topics  
⚠️ Personal journal entries may differ from other text types  
⚠️ Potential class imbalance (distribution of negative/neutral/positive)

## Performance Metrics

### Model Evaluation

Performance metrics are printed during training via `classification_report`:

#### Expected Performance Ranges

Based on typical text classification tasks:

- **Overall Accuracy**: 75-85% (varies with data quality)
- **Macro Average F1**: 0.70-0.80
- **Weighted Average F1**: 0.75-0.85

#### Per-Class Metrics

Typical performance (actual values depend on training data):

| Class    | Precision | Recall    | F1-Score  | Notes                      |
| -------- | --------- | --------- | --------- | -------------------------- |
| Negative | 0.75-0.85 | 0.70-0.80 | 0.72-0.82 | May be easiest to detect   |
| Neutral  | 0.65-0.75 | 0.70-0.80 | 0.67-0.77 | Hardest class (ambiguous)  |
| Positive | 0.75-0.85 | 0.75-0.85 | 0.75-0.85 | Strong positive indicators |

**Note**: Actual performance varies significantly based on training data quality and quantity.

### Feature Importance

TF-IDF learns which words/phrases are most indicative of each emotion:

**Typical Negative Indicators**:

- Words: sad, worried, anxious, difficult, struggle, bad, upset, frustrated
- Bigrams: "feel bad", "so hard", "can't cope"

**Typical Positive Indicators**:

- Words: happy, great, wonderful, excited, grateful, love, amazing, good
- Bigrams: "feel great", "so happy", "going well"

**Neutral Indicators**:

- Words: today, went, did, usual, normal, work, school
- Bigrams: "as usual", "nothing special"

### Performance Considerations

- Performance highly dependent on training data size and quality
- Short entries may be harder to classify (less context)
- Sarcasm or mixed emotions not well captured
- New vocabulary (slang, domain-specific terms) may not be recognized

## Model Behavior

### Decision Process

1. **Text Input**: User journal entry as string
2. **Vectorization**: TF-IDF transforms text to 3000-dimensional vector
3. **Classification**: Logistic regression computes probabilities for 3 classes
4. **Prediction**: Class with highest probability is returned

### Confidence Levels

- **High Confidence**: Clear emotional language (e.g., "I'm so happy today!")
- **Medium Confidence**: Mixed or moderate emotional signals
- **Low Confidence**: Neutral, factual, or ambiguous text

### Edge Cases

1. **Empty/Very Short Text**: May default to neutral or have low confidence
2. **Mixed Emotions**: "I'm happy but also worried" - classifies based on dominant tone
3. **Sarcasm**: "Yeah, great day..." - may misclassify as positive
4. **Negation**: "Not happy" - effectiveness depends on training data
5. **Unknown Words**: Out-of-vocabulary words ignored by TF-IDF

## Ethical Considerations

### Privacy and Sensitivity

#### Personal Content

- ⚠️ **Critical**: Journal entries are highly personal and sensitive
- ⚠️ Text may contain private information, feelings, or experiences
- ✅ Model processes text locally (no external API calls)
- ⚠️ Predictions stored in database - ensure proper access controls

#### Mental Health Context

- ⚠️ Emotional classification may oversimplify complex feelings
- ⚠️ Could miss nuanced mental health signals
- ⚠️ Should not be used for crisis detection or intervention decisions
- ✅ Provides general sentiment trends, not clinical assessment

### Fairness and Bias

#### Language Bias

- ⚠️ Trained on English text - not suitable for other languages
- ⚠️ May perform differently on non-native English speakers
- ⚠️ Vocabulary and expression styles vary across demographics

#### Cultural Bias

- ⚠️ Emotional expression varies across cultures
- ⚠️ What's considered "positive" or "negative" is culturally dependent
- ⚠️ Western emotional concepts may not universally apply

#### Age Bias

- ⚠️ Writing styles differ by age (teen slang vs adult language)
- ⚠️ Unknown: Model performance across age groups
- ❓ Training data age distribution unknown

#### Gender Bias

- ⚠️ Emotional expression patterns may differ by gender
- ⚠️ Training data gender balance unknown
- ❓ Potential differential performance not evaluated

### Transparency

- ✅ Open source implementation
- ✅ Simple, interpretable model (Logistic Regression)
- ✅ TF-IDF features are human-readable (word importance)
- ⚠️ Training data and labels not publicly documented

### User Impact

- ⚠️ Classifications shown to users may influence self-perception
- ⚠️ Misclassification could invalidate user's emotional experience
- ⚠️ Users may alter writing to achieve desired classification
- ✅ Simple 3-class system reduces over-interpretation risk

## Limitations

### Technical Limitations

1. **Training Data Dependency**: Performance entirely dependent on database contents
2. **Fixed Vocabulary**: Can't recognize words not in training data
3. **No Context Memory**: Each entry classified independently
4. **3-Class Simplification**: Real emotions more complex than positive/neutral/negative
5. **No Intensity Levels**: "slightly happy" vs "ecstatic" both classified as positive
6. **Short Text Challenge**: Brief entries provide little information
7. **No Temporal Modeling**: Doesn't consider emotion changes over time

### Linguistic Limitations

1. **Sarcasm Blindness**: Cannot detect sarcastic or ironic language
2. **Negation Handling**: "not happy" may not be properly understood
3. **Mixed Emotions**: Can only assign one label, misses emotional complexity
4. **Metaphors/Idioms**: May misinterpret figurative language
5. **Misspellings**: TF-IDF treats misspelled words as unknown
6. **Domain-Specific Language**: Medical, technical terms may be misclassified

### Conceptual Limitations

1. **Emotion Reduction**: 3 categories vastly oversimplify human emotion
2. **Subjective Labels**: What's "positive" vs "neutral" is subjective
3. **No Emotion Intensity**: Can't distinguish mild from intense emotions
4. **Static Model**: Doesn't learn from new entries without retraining
5. **Individual Differences**: People express same emotions differently

### Deployment Limitations

1. **Model File Size**: Vectorizer + model requires storage (~1-5 MB)
2. **Prediction Latency**: Vectorization adds computational overhead
3. **Memory Usage**: 3000-feature vectors require memory
4. **Version Compatibility**: Requires exact scikit-learn version for joblib loading
5. **No Confidence Scores**: Current implementation only returns class label

## Recommendations

### For Implementation

1. ✅ **User Transparency**: Show users their emotion classifications
2. ✅ **Allow Corrections**: Let users correct misclassifications
3. ✅ **Display Confidence**: Show when model is uncertain
4. ✅ **Privacy Controls**: Secure storage of journal entries
5. ✅ **Opt-In**: Make emotion analysis optional

### For Improvement

1. 🔄 **Expand Classes**: Add more nuanced emotions (worried, excited, angry, etc.)
2. 🔄 **Add Confidence Scores**: Return probabilities, not just class
3. 🔄 **Real Training Data**: Use actual labeled journal entries
4. 🔄 **Active Learning**: Allow users to correct labels for retraining
5. 🔄 **Multi-Label**: Support mixed emotions (happy AND anxious)
6. 🔄 **Temporal Modeling**: Track emotion changes over time
7. 🔄 **Better Features**: Experiment with BERT embeddings or other representations

### For Monitoring

1. 📊 **Class Distribution**: Track if predictions are imbalanced
2. 📊 **User Feedback**: Collect corrections when users disagree
3. 📊 **Confidence Tracking**: Monitor average prediction confidence
4. 📊 **Error Analysis**: Review misclassified examples
5. 📊 **Drift Detection**: Check if text patterns change over time

### For Users

1. 👤 **Understand Limitations**: Emotion classification is approximate
2. 👤 **Provide Feedback**: Correct wrong classifications to help improve
3. 👤 **View as Trends**: Individual classifications may be wrong, patterns more reliable
4. 👤 **Write Naturally**: Don't alter writing to achieve desired classification
5. 👤 **Complement, Don't Replace**: Use alongside self-reflection, not instead of

## Caveats and Warnings

### ⚠️ Critical Warnings

- **DO NOT** use for crisis detection or suicide risk assessment
- **DO NOT** make clinical decisions based on classifications
- **DO NOT** assume classifications are accurate for individuals
- **DO NOT** use on languages other than English
- **DO NOT** share user journal entries without explicit consent

### 🔴 Known Issues

1. Training data quality and quantity unknown
2. No validation dataset - only test set used once
3. Model may overfit to specific writing styles in training data
4. No bias testing performed across demographics
5. No confidence thresholds defined for uncertain predictions
6. Current implementation discards probability scores

### ⚠️ Ethical Red Flags

- Journal entries contain highly sensitive personal information
- Misclassification could invalidate genuine emotional experiences
- Potential for users to game the system (write for desired classification)
- No mechanism for handling crisis-related text
- Unknown impact on user self-perception and emotional awareness

## Technical Specifications

### Model Interface

```python
from Emotion_Classification.predict import predict_emotion

# Predict emotion from text
text = "I had a really great day today! Everything went well."
emotion = predict_emotion(text)  # Returns: "positive", "neutral", or "negative"

print(f"Detected emotion: {emotion}")
```

### Input Requirements

- **Type**: String (text)
- **Encoding**: UTF-8
- **Length**: Flexible (works best with 10-200 words)
- **Language**: English only
- **Format**: Plain text (no HTML, markdown, etc.)

### Output Format

- **Type**: String
- **Values**: "negative", "neutral", or "positive"
- **No probabilities returned** (current implementation)

### Model Persistence

```python
# Model saved as pickle file
import joblib

bundle = joblib.load("Emotion_Classification/model.pkl")
model = bundle["model"]          # Logistic Regression model
vectorizer = bundle["vectorizer"] # TF-IDF vectorizer
```

### Dependencies

- **Python**: 3.7+
- **scikit-learn**: 0.24+ (for TF-IDF and Logistic Regression)
- **joblib**: 1.0+ (for model serialization)
- **sqlite3**: Built-in (for data loading during training)

### Training Script

```bash
# Train/retrain the model
python -m Emotion_Classification.train

# Outputs:
# - Classification report with metrics
# - Saved model to Emotion_Classification/model.pkl
```

## Model Versioning

### Version History

#### v1.0.0 (January 2026) - Initial Release

- First production version
- Logistic Regression with TF-IDF (3000 features)
- 3-class emotion classification (negative/neutral/positive)
- Trained on journal entries from database
- Test accuracy: Varies with training data

### Versioning Strategy

- Model saved as `model.pkl` with timestamp
- Version tracked in code comments
- Retraining creates new model file (manual backup needed)
- No automated versioning system currently implemented

### Future Versioning Plans

- Integrate with `model_versioning.py` system
- Track training data versions
- Log hyperparameters and metrics
- Enable A/B testing of model versions

## Data Sheet

### Data Collection

- **Method**: User-generated journal entries via Soul Sense app
- **Consent**: Users consent to journal feature usage
- **Labeling**: Labels stored in database (labeling process unknown)
- **Quality Control**: Unknown labeling validation process

### Data Composition

- **Size**: Depends on database accumulation
- **Timeframe**: Ongoing collection
- **Demographics**: User population of Soul Sense app
- **Language**: English (assumed)
- **Label Distribution**: Unknown (should be monitored)

### Data Preprocessing

1. Text extracted from database
2. Converted to TF-IDF vectors
3. English stop words removed
4. Vocabulary limited to 3000 features
5. Unigrams and bigrams included

### Data Privacy

- Journal entries contain PII and sensitive information
- Stored locally in SQLite database
- Access control via application authentication
- Model training data should be anonymized
- GDPR/CCPA compliance considerations needed

## References

### Scientific Literature

1. Pang, B., & Lee, L. (2008). "Opinion Mining and Sentiment Analysis." _Foundations and Trends in Information Retrieval_.
2. Mohammad, S. M. (2016). "Sentiment Analysis: Detecting Valence, Emotions, and Other Affectual States from Text."
3. Pennebaker, J. W. (1997). "Writing About Emotional Experiences as a Therapeutic Process."

### Technical References

1. Pedregosa, F., et al. (2011). "Scikit-learn: Machine Learning in Python." _JMLR_.
2. Ramos, J. (2003). "Using TF-IDF to Determine Word Relevance in Document Queries."
3. Mitchell, M., et al. (2019). "Model Cards for Model Reporting."

### Related Documentation

- See `Emotion_Classification/README` for module overview
- See `PRIVACY.md` for data privacy policies
- See `ETHICAL_CONSIDERATIONS.md` for broader ethical context
- See `labels.py` for emotion label definitions

## Glossary

- **TF-IDF**: Term Frequency-Inverse Document Frequency - weighting scheme for text features
- **N-gram**: Sequence of N consecutive words (1-gram = single word, 2-gram = word pair)
- **Stop words**: Common words (the, is, and) typically removed from analysis
- **One-vs-Rest (OvR)**: Multi-class strategy where each class is compared against all others
- **Logistic Regression**: Linear model for classification using logistic/sigmoid function
- **Vectorization**: Converting text to numerical feature vectors

---

## Change Log

### v1.0.0 - January 2026

- Initial model card creation
- Documented TF-IDF + Logistic Regression approach
- Listed limitations and ethical considerations
- Added recommendations for improvement

---

**Model Card Version**: 1.0  
**Last Updated**: January 10, 2026  
**Next Review Date**: April 2026 (or upon model update)

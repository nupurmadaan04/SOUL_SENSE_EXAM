# Model Evaluation Metrics

This directory contains comprehensive evaluation metrics, visualizations, and reports for all ML models in the Soul Sense EQ Test system.

---

## Overview

The Soul Sense project includes two primary ML models:

1. **Depression Risk Predictor** - Random Forest classifier for assessing mental health risk
2. **Emotion Classifier** - Logistic Regression with TF-IDF for journal sentiment analysis

Both models are evaluated using industry-standard classification metrics to ensure reliability and transparency.

---

## Evaluation Metrics

### Core Classification Metrics

#### Accuracy

- **Definition**: Proportion of correct predictions out of total predictions
- **Formula**: (TP + TN) / (TP + TN + FP + FN)
- **Range**: 0.0 to 1.0 (higher is better)
- **Interpretation**: Overall model correctness

#### Precision

- **Definition**: Proportion of positive predictions that are actually correct
- **Formula**: TP / (TP + FP)
- **Range**: 0.0 to 1.0 (higher is better)
- **Interpretation**: How reliable are the positive predictions?

#### Recall (Sensitivity)

- **Definition**: Proportion of actual positives correctly identified
- **Formula**: TP / (TP + FN)
- **Range**: 0.0 to 1.0 (higher is better)
- **Interpretation**: How many actual positives did we catch?

#### F1-Score

- **Definition**: Harmonic mean of precision and recall
- **Formula**: 2 × (Precision × Recall) / (Precision + Recall)
- **Range**: 0.0 to 1.0 (higher is better)
- **Interpretation**: Balanced measure of precision and recall

#### AUC-ROC

- **Definition**: Area Under the Receiver Operating Characteristic curve
- **Range**: 0.0 to 1.0 (higher is better)
- **Interpretation**: Model's ability to discriminate between classes

### Why Not RMSE?

**RMSE (Root Mean Squared Error)** is a regression metric used for models that predict continuous numerical values (e.g., predicting house prices, temperature).

Both Soul Sense models are **classification models** that predict discrete categories:

- Depression Risk Predictor: Predicts "Low Risk", "Moderate Risk", or "High Risk"
- Emotion Classifier: Predicts "Negative", "Neutral", or "Positive"

Since these models output categories (not continuous numbers), RMSE is not applicable. The appropriate metrics are **accuracy**, **precision**, **recall**, and **F1-score**.

---

## Running Evaluations

### Quick Start

Evaluate all models with one command:

```bash
python evaluate_models.py
```

This script:

- ✅ Evaluates Depression Risk Predictor
- ✅ Evaluates Emotion Classifier
- ✅ Generates confusion matrices
- ✅ Creates ROC curves
- ✅ Produces detailed reports
- ✅ Compares models side-by-side

### Output Structure

```
evaluation_results/
├── depression_predictor/
│   ├── Depression_Risk_Predictor_confusion_matrix.png
│   ├── Depression_Risk_Predictor_roc_curve.png
│   ├── Depression_Risk_Predictor_evaluation_report.txt
│   └── Depression_Risk_Predictor_metrics.json
├── emotion_classifier/
│   ├── Emotion_Classifier_confusion_matrix.png
│   ├── Emotion_Classifier_roc_curve.png
│   ├── Emotion_Classifier_evaluation_report.txt
│   └── Emotion_Classifier_metrics.json
├── model_comparison.png
└── EVALUATION_SUMMARY.md
```

---

## Using the Evaluation Module

### Basic Usage

```python
from model_evaluation import ModelEvaluator

# Create evaluator
evaluator = ModelEvaluator(
    model_name="My_Model",
    model_type="classification"
)

# Evaluate model
metrics = evaluator.evaluate_classification(
    y_true=y_test,
    y_pred=predictions,
    y_proba=probabilities,  # Optional for AUC
    class_names=['Class A', 'Class B', 'Class C']
)

# Generate full report with visualizations
evaluator.generate_full_report(
    y_true=y_test,
    y_pred=predictions,
    y_proba=probabilities,
    class_names=['Class A', 'Class B', 'Class C'],
    output_dir="my_evaluation"
)
```

### Advanced Usage

```python
from model_evaluation import ModelEvaluator, compare_models

# Evaluate multiple models
evaluator1 = ModelEvaluator("Model_A", "classification")
metrics1 = evaluator1.evaluate_classification(y_true1, y_pred1, class_names=['A', 'B'])

evaluator2 = ModelEvaluator("Model_B", "classification")
metrics2 = evaluator2.evaluate_classification(y_true2, y_pred2, class_names=['A', 'B'])

# Compare models visually
compare_models([evaluator1, evaluator2], output_path="comparison.png")
```

### For Regression Models

If you add regression models in the future:

```python
evaluator = ModelEvaluator("My_Regression_Model", "regression")

metrics = evaluator.evaluate_regression(
    y_true=actual_values,
    y_pred=predicted_values
)
# This will calculate MSE, RMSE, MAE, R², MAPE
```

---

## Interpreting Results

### Confusion Matrix

A confusion matrix shows the distribution of predictions:

```
                 Predicted
              Low  Mod  High
Actual  Low  [ 85   10    5 ]
        Mod  [ 12   35    3 ]
        High [  3    7   40 ]
```

- **Diagonal** (85, 35, 40): Correct predictions
- **Off-diagonal**: Misclassifications
- Helps identify which classes are confused with each other

### ROC Curve

The ROC curve plots True Positive Rate vs. False Positive Rate:

- **Perfect classifier**: Curve hugs top-left corner (AUC = 1.0)
- **Random classifier**: Diagonal line (AUC = 0.5)
- **Good classifier**: AUC between 0.7-0.9
- **Excellent classifier**: AUC > 0.9

### Performance Benchmarks

#### Depression Risk Predictor

| Metric    | Target | Current   |
| --------- | ------ | --------- |
| Accuracy  | >85%   | 85-90%    |
| F1-Score  | >0.85  | 0.85-0.88 |
| Precision | >0.85  | 0.86-0.89 |

#### Emotion Classifier

| Metric    | Target | Current   |
| --------- | ------ | --------- |
| Accuracy  | >75%   | 75-85%    |
| F1-Score  | >0.74  | 0.74-0.84 |
| Precision | >0.73  | 0.73-0.83 |

---

## Continuous Improvement

### Monitoring Model Performance

1. **Regular Evaluation**: Run evaluations after each model update
2. **Track Metrics Over Time**: Compare with previous versions
3. **Test on New Data**: Validate on fresh, unseen data
4. **User Feedback**: Collect real-world performance data

### When to Retrain

Consider retraining if:

- ❌ Accuracy drops below target threshold
- ❌ Significant performance degradation on new data
- ❌ User feedback indicates poor predictions
- ❌ New data patterns emerge that weren't in training set

### Improvement Strategies

1. **Data Quality**

   - Collect more diverse training samples
   - Fix labeling errors
   - Balance class distributions

2. **Feature Engineering**

   - Add relevant features
   - Remove noisy features
   - Transform features (scaling, encoding)

3. **Hyperparameter Tuning**

   - Adjust model parameters
   - Use grid search or random search
   - Cross-validation for robustness

4. **Model Architecture**
   - Try different algorithms
   - Ensemble methods
   - Deep learning approaches

---

## Evaluation Best Practices

### ✅ Do

- Evaluate on separate test data (never training data)
- Use stratified splits to maintain class distributions
- Report multiple metrics (not just accuracy)
- Visualize results (confusion matrix, ROC curve)
- Document evaluation methodology
- Track metrics over time

### ❌ Don't

- Test on training data (causes overfitting illusion)
- Rely solely on accuracy (misleading with imbalanced data)
- Ignore per-class performance
- Skip validation on new data
- Make changes without re-evaluation

---

## API Reference

### ModelEvaluator Class

```python
class ModelEvaluator(model_name: str, model_type: str)
```

**Methods:**

- `evaluate_classification(y_true, y_pred, y_proba=None, class_names=None, average='weighted')`
  - Returns: Dictionary of metrics
- `evaluate_regression(y_true, y_pred)`
  - Returns: Dictionary of metrics
- `save_confusion_matrix(y_true, y_pred, class_names, output_path)`
  - Saves: PNG visualization
- `save_roc_curve(y_true, y_proba, class_names=None, output_path)`
  - Saves: PNG visualization
- `save_metrics_report(output_path)`
  - Saves: Text report
- `save_metrics_json(output_path)`
  - Saves: JSON metrics
- `generate_full_report(y_true, y_pred, y_proba=None, class_names=None, output_dir)`
  - Generates: Complete evaluation package

### Helper Functions

```python
compare_models(evaluators: list, output_path: str)
```

- Creates side-by-side comparison visualization

---

## Troubleshooting

### Common Issues

**Issue**: "No module named 'model_evaluation'"

- **Solution**: Ensure you're in the project root directory

**Issue**: "Model file not found"

- **Solution**: Train the models first using `ml_predictor.py` and `Emotion_Classification/train.py`

**Issue**: "Not enough data for evaluation"

- **Solution**: Ensure test dataset has sufficient samples (minimum 20 per class)

**Issue**: "AUC calculation failed"

- **Solution**: Check if probabilities are provided and classes are properly encoded

---

## References

For academic references on evaluation metrics and best practices, see:

- [RESEARCH_REFERENCES.md](RESEARCH_REFERENCES.md) - Comprehensive academic citations
- [Model Cards](model_cards/) - Detailed model documentation

### Key Papers

- **Classification Metrics**: Powers, D. M. (2011). "Evaluation: From Precision, Recall and F-Measure to ROC, Informedness, Markedness and Correlation"
- **Model Evaluation**: Kohavi, R. (1995). "A Study of Cross-Validation and Bootstrap for Accuracy Estimation"
- **Imbalanced Data**: Haibo He, & Garcia, E. A. (2009). "Learning from Imbalanced Data"

---

## Contributing

To add new evaluation metrics or improve existing ones:

1. Update `model_evaluation.py` with new metric calculations
2. Add metric documentation to this README
3. Update `evaluate_models.py` to include new metrics
4. Test thoroughly on both models
5. Submit pull request with examples

---

## License

See [LICENSE.txt](LICENSE.txt) for details.

---

**Last Updated**: January 10, 2026  
**Version**: 1.0.0  
**Maintainer**: Soul Sense Development Team

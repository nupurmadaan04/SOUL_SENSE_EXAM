# Model Card Guidelines

This guide explains how to create, maintain, and use model cards for ML models in the Soul Sense EQ Test project.

## What Are Model Cards?

**Model cards** are short documents that provide transparent and standardized information about machine learning models. They help developers, users, and stakeholders understand:

- What the model does
- How it was trained
- How well it performs
- What its limitations are
- How it should (and shouldn't) be used
- Ethical considerations and potential biases

### Why Model Cards Matter

1. **Transparency**: Users understand what models do and how they work
2. **Accountability**: Clear documentation of model decisions and limitations
3. **Ethics**: Explicit discussion of fairness, bias, and potential harms
4. **Safety**: Warnings about misuse and inappropriate applications
5. **Trust**: Builds confidence through openness and honesty
6. **Compliance**: Helps meet regulatory requirements (GDPR, AI Act, etc.)

## When to Create a Model Card

Create a model card when:

- ✅ Adding a new ML model to the project
- ✅ Significantly updating an existing model
- ✅ Retraining a model with new data
- ✅ Changing model hyperparameters or architecture
- ✅ Deploying a model to production

## How to Create a Model Card

### Step 1: Start with the Template

Copy `MODEL_CARD_TEMPLATE.md` and rename it descriptively:

```bash
cp model_cards/MODEL_CARD_TEMPLATE.md model_cards/my_model_card.md
```

### Step 2: Fill in Model Details

- Provide basic information (name, type, version, location)
- Document architecture and hyperparameters
- List all dependencies and frameworks

### Step 3: Define Intended Use

- **Be specific** about what the model should be used for
- **Be explicit** about what it should NOT be used for
- Consider different user types and their needs

### Step 4: Document Training Data

- Describe data sources and collection methods
- Document sample size and characteristics
- Explain labeling methodology
- **Be honest** about data limitations

### Step 5: Report Performance

- Include multiple metrics (accuracy, precision, recall, F1)
- Break down by class if multi-class classification
- Report on training, validation, AND test sets
- Discuss when the model performs well vs. poorly

### Step 6: Address Ethics

This is **critical** - don't skip or rush this section:

- Analyze potential biases (age, gender, culture, etc.)
- Discuss privacy implications
- Consider domain-specific ethical concerns
- Think about potential harms

### Step 7: List Limitations

**Be brutally honest** - this builds trust:

- Technical limitations (architecture, data, etc.)
- Domain limitations (what it doesn't capture)
- Deployment constraints
- Generalization limits (when it doesn't work)

### Step 8: Provide Recommendations

- Best practices for implementation
- Ideas for improvement
- Monitoring strategies
- User guidance

### Step 9: Add Warnings

**Make these prominent**:

- Critical warnings about misuse
- Known issues and bugs
- Ethical red flags
- Safety concerns

### Step 10: Include Technical Specs

- Code examples for using the model
- Input/output specifications
- Dependencies with versions
- Version history

## Model Card Sections Explained

### Model Details

**Purpose**: Basic identification and architecture information  
**Key Questions**:

- What is this model and what does it do?
- What algorithm/architecture does it use?
- When was it created and by whom?

**Tips**:

- Use clear, descriptive names
- Version models semantically (MAJOR.MINOR.PATCH)
- Document all hyperparameters

### Intended Use

**Purpose**: Define appropriate and inappropriate applications  
**Key Questions**:

- Who should use this model?
- What problems is it designed to solve?
- What should it absolutely NOT be used for?

**Tips**:

- Be specific about use cases
- Explicitly list out-of-scope uses
- Consider different stakeholder perspectives

### Training Data

**Purpose**: Transparency about what the model learned from  
**Key Questions**:

- Where did the training data come from?
- How was it labeled?
- What are its characteristics and limitations?

**Tips**:

- Document sample sizes
- Describe demographic distributions
- Admit data quality issues honestly

### Performance Metrics

**Purpose**: Quantify how well the model works  
**Key Questions**:

- How accurate is the model?
- Does performance vary across classes or groups?
- Where does the model succeed and fail?

**Tips**:

- Include multiple metrics
- Report on separate test set
- Break down by subgroups when possible

### Ethical Considerations

**Purpose**: Address fairness, bias, privacy, and potential harms  
**Key Questions**:

- Could this model discriminate against certain groups?
- What privacy risks exist?
- What harms could misuse cause?

**Tips**:

- Don't assume "objective" models are unbiased
- Consider intersectional biases
- Think about indirect harms

### Limitations

**Purpose**: Honest disclosure of what the model can't do  
**Key Questions**:

- What are the model's blind spots?
- When will it fail or perform poorly?
- What assumptions is it making?

**Tips**:

- Be comprehensive
- Include technical AND conceptual limitations
- Don't hide known issues

### Recommendations

**Purpose**: Guide users toward best practices  
**Key Questions**:

- How should this model be deployed safely?
- What monitoring is needed?
- How can it be improved?

**Tips**:

- Provide actionable guidance
- Suggest complementary approaches
- Recommend monitoring strategies

## Model Card Best Practices

### DO:

✅ **Be honest and transparent** - admit limitations and unknowns  
✅ **Use clear language** - avoid unnecessary jargon  
✅ **Include warnings** - make misuse risks explicit  
✅ **Update regularly** - keep cards current as models evolve  
✅ **Seek review** - have others read and provide feedback  
✅ **Link to code** - connect documentation to implementation  
✅ **Version control** - track changes to model cards over time

### DON'T:

❌ **Oversell performance** - don't cherry-pick metrics  
❌ **Hide limitations** - users need to know what doesn't work  
❌ **Ignore ethics** - fairness and bias always matter  
❌ **Use jargon unnecessarily** - write for non-experts  
❌ **Skip out-of-scope uses** - explicitly state what NOT to do  
❌ **Forget to update** - stale documentation is dangerous  
❌ **Make it marketing** - model cards are technical documentation

## Common Pitfalls to Avoid

### 1. Overconfidence

**Problem**: Presenting model as more accurate/reliable than it is  
**Solution**: Report performance on held-out test data, include confidence intervals, discuss failure modes

### 2. Ignoring Bias

**Problem**: Assuming model is "objective" or "neutral"  
**Solution**: Actively test for demographic biases, consider cultural context, analyze fairness metrics

### 3. Vague Use Cases

**Problem**: "Can be used for sentiment analysis" is too broad  
**Solution**: Be specific - "Classifies English journal entries into 3 emotion categories"

### 4. Missing Limitations

**Problem**: Only describing what model CAN do  
**Solution**: Dedicate equal attention to what it CANNOT or SHOULD NOT do

### 5. Technical-Only Focus

**Problem**: Only documenting technical specs, ignoring social context  
**Solution**: Balance technical details with ethical considerations and user guidance

### 6. Stale Documentation

**Problem**: Model card not updated when model is retrained  
**Solution**: Make model card updates part of your development workflow

### 7. No Warnings

**Problem**: Failing to warn about dangerous or inappropriate uses  
**Solution**: Prominently display critical warnings and ethical red flags

## Example Model Card Structure

Here's a recommended minimal structure (expand as needed):

```markdown
# Model Card: [Model Name]

## Quick Facts

- **What it does**: [One sentence]
- **Current Version**: vX.Y.Z
- **Performance**: [Key metric]
- **Use it for**: [Primary use]
- **Don't use it for**: [Critical misuse]

## [Full Sections as in Template]

## Critical Warnings

[Prominently display most important warnings]
```

## Reviewing Model Cards

When reviewing a model card (yours or someone else's), check:

### Completeness Checklist

- [ ] All template sections filled in (or marked N/A with explanation)
- [ ] Performance metrics reported with methodology
- [ ] Training data characteristics documented
- [ ] Ethical considerations addressed
- [ ] Limitations listed honestly
- [ ] Out-of-scope uses explicitly stated
- [ ] Technical specifications allow reproduction
- [ ] Critical warnings prominently displayed
- [ ] Version information included
- [ ] Contact information provided

### Quality Checklist

- [ ] Language is clear and accessible
- [ ] Claims are supported by evidence
- [ ] Limitations are honestly disclosed
- [ ] Ethical concerns are thoughtfully addressed
- [ ] Recommendations are actionable
- [ ] Code examples are functional
- [ ] References are complete and accurate

### Ethics Checklist

- [ ] Potential biases analyzed
- [ ] Privacy implications discussed
- [ ] Potential harms considered
- [ ] Mitigation strategies provided
- [ ] Fairness across groups addressed
- [ ] Transparency mechanisms described

## Maintaining Model Cards

### When to Update

Update the model card when:

- Model is retrained with new data
- Hyperparameters are changed
- New limitations or biases are discovered
- Performance metrics change
- Deployment context changes
- User feedback reveals issues

### Versioning Model Cards

- Use semantic versioning for models
- Document changes in Change Log section
- Keep old versions in git history
- Note what changed and why

### Periodic Review

Schedule regular reviews (quarterly or semi-annually):

- Verify information is still accurate
- Check if new research affects recommendations
- Update performance metrics if model has drifted
- Reassess ethical considerations

## Model Cards in Development Workflow

### Integration Points

#### 1. During Development

- Draft model card as you develop
- Use card to think through design decisions
- Document choices and trade-offs

#### 2. Before Deployment

- Complete all sections
- Have card reviewed by team
- Ensure warnings are clear
- Verify technical specs

#### 3. After Deployment

- Monitor actual performance vs. card claims
- Update with real-world learnings
- Add newly discovered limitations
- Track user feedback

#### 4. Regular Maintenance

- Scheduled reviews (quarterly)
- Update performance metrics
- Add new research or findings
- Refine recommendations

## Soul Sense Specific Guidelines

### For Depression Risk Predictor

- **Emphasize**: Not for clinical diagnosis
- **Highlight**: Synthetic training data limitation
- **Warn**: Not validated against actual depression
- **Recommend**: Professional consultation for concerns

### For Emotion Classifier

- **Emphasize**: Privacy of journal entries
- **Highlight**: Training data dependency
- **Warn**: Oversimplification of complex emotions
- **Recommend**: User feedback for corrections

### For Future Models

- Follow established template
- Maintain consistency in structure
- Link to related model cards
- Document interactions between models

## Resources

### Academic Papers

- Mitchell et al. (2019). "Model Cards for Model Reporting"
- Gebru et al. (2018). "Datasheets for Datasets"
- Raji et al. (2020). "Closing the AI Accountability Gap"

### Industry Examples

- Google Cloud Model Cards
- Hugging Face Model Cards
- Microsoft Azure Responsible AI
- Partnership on AI Model Cards

### Project Documents

- `ETHICAL_CONSIDERATIONS.md` - Broader ethical context
- `PRIVACY.md` - Data privacy policies
- `SECURITY.md` - Security considerations
- `AUTHORS.md` - Contributor information

## Getting Help

If you need assistance creating or reviewing a model card:

1. **Consult Examples**: Review existing model cards in this directory
2. **Use Template**: Start with `MODEL_CARD_TEMPLATE.md`
3. **Ask Team**: Request review from colleagues
4. **Check Resources**: Review academic papers and industry examples
5. **Iterate**: Model cards improve with feedback and updates

## Contributing

To contribute to model card documentation:

1. Fork the repository
2. Create a new model card from template
3. Fill in all sections completely
4. Have someone review your card
5. Submit pull request with clear description
6. Address review feedback

---

## Summary

Model cards are essential for:

- 🔍 **Transparency** - Open documentation of models
- ⚖️ **Accountability** - Clear responsibility for model behavior
- 🛡️ **Safety** - Explicit warnings about misuse
- 🤝 **Trust** - Builds confidence through honesty
- 📋 **Compliance** - Meets regulatory requirements

**Key Principles**:

1. Be honest about limitations
2. Address ethical concerns seriously
3. Write for diverse audiences
4. Update regularly
5. Seek feedback and review

---

**Last Updated**: January 10, 2026  
**Document Version**: 1.0

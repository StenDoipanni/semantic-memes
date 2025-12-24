# BLIP2-Flan-T5-xl Evaluation Results

## Overview
Evaluation of BLIP2-Flan-T5-xl model on the hateful memes Q&A dataset.

## Overall Performance

| Metric | Value |
|--------|-------|
| **Total Questions** | 42 |
| **Correct Answers** | 6 |
| **Incorrect Answers** | 36 |
| **Overall Accuracy** | **14.29%** |

## Per-Dimension Statistics

| Dimension | Correct | Total | Accuracy |
|-----------|---------|------|----------|
| ToxicityAssessment | 6 | 42 | **14.29%** |

## Performance Insights

- **Low Performance**: The model achieved only 14.29% accuracy, correctly answering only 6 out of 42 toxicity assessment questions.
- **Significant Challenges**: The model struggled significantly with toxicity assessment, suggesting it may have difficulty understanding nuanced hate speech classification.
- **Coverage**: All 42 questions evaluated were from the ToxicityAssessment dimension.

## Comparison with Qwen2-VL-7B-Instruct

| Model | Accuracy | Correct/Total |
|-------|----------|---------------|
| **Qwen2-VL-7B-Instruct** | 76.19% | 32/42 |
| **BLIP2-Flan-T5-xl** | 14.29% | 6/42 |

**Performance Gap**: Qwen2-VL-7B-Instruct outperforms BLIP2-Flan-T5-xl by **61.90 percentage points**.

## Generated Visualizations

The following visualizations have been generated:

1. **accuracy_by_dimension.png** - Bar chart showing accuracy by dimension
2. **correct_incorrect_distribution.png** - Stacked bar chart of correct vs incorrect answers
3. **overall_summary.png** - Pie chart of overall accuracy and questions per dimension
4. **statistics.csv** - Detailed statistics in CSV format
5. **full_results.csv** - Complete results for all questions

## Files Location

All results and visualizations are saved in:
```
/home/stefano/memes/semantic-memes/output_reversed/qa-test-huawei/results/BLIP2-Flan-T5-xl/
```









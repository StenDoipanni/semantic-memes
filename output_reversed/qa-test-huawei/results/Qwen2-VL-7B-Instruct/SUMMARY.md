# Qwen2-VL-7B-Instruct Evaluation Results

## Overview
Evaluation of Qwen2-VL-7B-Instruct model on the hateful memes Q&A dataset.

## Overall Performance

| Metric | Value |
|--------|-------|
| **Total Questions** | 42 |
| **Correct Answers** | 32 |
| **Incorrect Answers** | 10 |
| **Overall Accuracy** | **76.19%** |

## Per-Dimension Statistics

| Dimension | Correct | Total | Accuracy |
|-----------|---------|------|----------|
| ToxicityAssessment | 32 | 42 | **76.19%** |

## Error Analysis

The model made **10 incorrect predictions** out of 42 questions. The errors are distributed as follows:

| Image ID | Expected Answer | Model Answer | Status |
|----------|----------------|--------------|--------|
| 01974 | A | C | ❌ |
| 06378 | C | B | ❌ |
| 04762 | D | C | ❌ |
| 03865 | C | D | ❌ |
| 01382 | C | A | ❌ |
| 05726 | D | B | ❌ |
| 05869 | D | B | ❌ |
| 02849 | A | B | ❌ |
| 07389 | D | A | ❌ |
| 05642 | A | C | ❌ |

## Performance Insights

- **Strong Performance**: The model achieved 76.19% accuracy, correctly answering 32 out of 42 toxicity assessment questions.
- **Error Pattern**: The model shows some confusion between different toxicity levels (A, B, C, D), suggesting the task requires fine-grained understanding of hate speech nuances.
- **Coverage**: All 42 questions evaluated were from the ToxicityAssessment dimension.

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
/home/stefano/memes/semantic-memes/output_reversed/qa-test-huawei/results/Qwen2-VL-7B-Instruct/
```









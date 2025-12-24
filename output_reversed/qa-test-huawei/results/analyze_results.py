#!/usr/bin/env python3
"""
Analyze Qwen2-VL-7B-Instruct evaluation results
"""

import json
import os
from pathlib import Path
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)

# Results directory
results_dir = Path("/home/stefano/memes/semantic-memes/output_reversed/qa-test-huawei/results/Qwen2-VL-7B-Instruct/outputs")

# Load all results
results = []
dimension_stats = defaultdict(lambda: {'correct': 0, 'total': 0, 'details': []})

for json_file in results_dir.glob("*.json"):
    with open(json_file, 'r') as f:
        data = json.load(f)
        
        # Extract key information
        dimension = data.get('dimension', 'Unknown')
        ground_truth = data.get('ground_truth_label', '').strip()
        model_choice = data.get('model_choice', '').strip()
        is_correct = ground_truth == model_choice
        
        results.append({
            'dimension': dimension,
            'image_id': json_file.stem.split('_')[0],
            'ground_truth': ground_truth,
            'model_choice': model_choice,
            'correct': is_correct,
            'question': data.get('question', ''),
            'ground_truth_text': data.get('ground_truth_text', ''),
        })
        
        dimension_stats[dimension]['total'] += 1
        if is_correct:
            dimension_stats[dimension]['correct'] += 1
        dimension_stats[dimension]['details'].append({
            'image_id': json_file.stem.split('_')[0],
            'correct': is_correct,
            'ground_truth': ground_truth,
            'model_choice': model_choice
        })

# Convert to DataFrame
df = pd.DataFrame(results)

# Print statistics
print("=" * 80)
print("Qwen2-VL-7B-Instruct Evaluation Results")
print("=" * 80)
print()

# Overall statistics
total_questions = len(results)
total_correct = df['correct'].sum()
overall_accuracy = (total_correct / total_questions) * 100

print(f"Overall Statistics:")
print(f"  Total Questions: {total_questions}")
print(f"  Correct Answers: {total_correct}")
print(f"  Accuracy: {overall_accuracy:.2f}%")
print()

# Per-dimension statistics
print("Per-Dimension Statistics:")
print("-" * 80)
dimension_accuracies = []
for dim in sorted(dimension_stats.keys()):
    stats = dimension_stats[dim]
    accuracy = (stats['correct'] / stats['total']) * 100 if stats['total'] > 0 else 0
    dimension_accuracies.append({
        'dimension': dim,
        'correct': stats['correct'],
        'total': stats['total'],
        'accuracy': accuracy
    })
    print(f"  {dim:25s} {stats['correct']:3d}/{stats['total']:3d} = {accuracy:6.2f}%")

print()

# Create visualizations
output_dir = Path("/home/stefano/memes/semantic-memes/output_reversed/qa-test-huawei/results/Qwen2-VL-7B-Instruct")
output_dir.mkdir(parents=True, exist_ok=True)

# 1. Accuracy by Dimension (Bar Chart)
fig, ax = plt.subplots(figsize=(14, 8))
dim_df = pd.DataFrame(dimension_accuracies).sort_values('accuracy', ascending=False)
colors = ['#2ecc71' if acc >= 70 else '#f39c12' if acc >= 50 else '#e74c3c' for acc in dim_df['accuracy']]
bars = ax.barh(dim_df['dimension'], dim_df['accuracy'], color=colors, alpha=0.8)
ax.set_xlabel('Accuracy (%)', fontsize=12, fontweight='bold')
ax.set_ylabel('Dimension', fontsize=12, fontweight='bold')
ax.set_title('Qwen2-VL-7B-Instruct: Accuracy by Dimension', fontsize=14, fontweight='bold')
ax.set_xlim(0, 100)
ax.grid(axis='x', alpha=0.3)

# Add value labels on bars
for i, (idx, row) in enumerate(dim_df.iterrows()):
    ax.text(row['accuracy'] + 1, i, f"{row['accuracy']:.1f}% ({row['correct']}/{row['total']})", 
            va='center', fontsize=10, fontweight='bold')

# Add overall accuracy line
ax.axvline(x=overall_accuracy, color='red', linestyle='--', linewidth=2, label=f'Overall: {overall_accuracy:.2f}%')
ax.legend()

plt.tight_layout()
plt.savefig(output_dir / 'accuracy_by_dimension.png', dpi=300, bbox_inches='tight')
print(f"✓ Saved: accuracy_by_dimension.png")
plt.close()

# 2. Distribution of Correct/Incorrect Answers
fig, ax = plt.subplots(figsize=(10, 6))
correct_counts = df.groupby('dimension')['correct'].value_counts().unstack(fill_value=0)
correct_counts.plot(kind='bar', stacked=True, ax=ax, color=['#e74c3c', '#2ecc71'], alpha=0.8)
ax.set_xlabel('Dimension', fontsize=12, fontweight='bold')
ax.set_ylabel('Number of Questions', fontsize=12, fontweight='bold')
ax.set_title('Qwen2-VL-7B-Instruct: Correct vs Incorrect Answers by Dimension', fontsize=14, fontweight='bold')
ax.legend(['Incorrect', 'Correct'], loc='upper right')
plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
plt.tight_layout()
plt.savefig(output_dir / 'correct_incorrect_distribution.png', dpi=300, bbox_inches='tight')
print(f"✓ Saved: correct_incorrect_distribution.png")
plt.close()

# 3. Overall Performance Summary
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# Pie chart: Overall accuracy
labels = ['Correct', 'Incorrect']
sizes = [total_correct, total_questions - total_correct]
colors_pie = ['#2ecc71', '#e74c3c']
explode = (0.05, 0)
ax1.pie(sizes, explode=explode, labels=labels, colors=colors_pie, autopct='%1.1f%%',
        shadow=True, startangle=90, textprops={'fontsize': 12, 'fontweight': 'bold'})
ax1.set_title(f'Overall Accuracy\n{overall_accuracy:.2f}%', fontsize=14, fontweight='bold')

# Bar chart: Questions per dimension
dim_counts = df['dimension'].value_counts().sort_values(ascending=True)
ax2.barh(dim_counts.index, dim_counts.values, color='#3498db', alpha=0.8)
ax2.set_xlabel('Number of Questions', fontsize=12, fontweight='bold')
ax2.set_ylabel('Dimension', fontsize=12, fontweight='bold')
ax2.set_title('Number of Questions per Dimension', fontsize=14, fontweight='bold')
ax2.grid(axis='x', alpha=0.3)

plt.tight_layout()
plt.savefig(output_dir / 'overall_summary.png', dpi=300, bbox_inches='tight')
print(f"✓ Saved: overall_summary.png")
plt.close()

# 4. Accuracy Heatmap (if we have multiple dimensions)
if len(dimension_accuracies) > 1:
    fig, ax = plt.subplots(figsize=(12, 8))
    dim_acc_df = pd.DataFrame(dimension_accuracies).sort_values('accuracy', ascending=False)
    # Create a simple visualization showing accuracy
    y_pos = range(len(dim_acc_df))
    bars = ax.barh(y_pos, dim_acc_df['accuracy'], 
                   color=['#2ecc71' if x >= 70 else '#f39c12' if x >= 50 else '#e74c3c' 
                          for x in dim_acc_df['accuracy']], alpha=0.8)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(dim_acc_df['dimension'], fontsize=11)
    ax.set_xlabel('Accuracy (%)', fontsize=12, fontweight='bold')
    ax.set_title('Qwen2-VL-7B-Instruct: Detailed Accuracy by Dimension', fontsize=14, fontweight='bold')
    ax.set_xlim(0, 100)
    ax.grid(axis='x', alpha=0.3)
    
    # Add detailed labels
    for i, (idx, row) in enumerate(dim_acc_df.iterrows()):
        ax.text(row['accuracy'] + 1, i, 
                f"{row['accuracy']:.1f}% | {row['correct']}/{row['total']} correct", 
                va='center', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'detailed_accuracy.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: detailed_accuracy.png")
    plt.close()

# Save detailed statistics to CSV
stats_df = pd.DataFrame(dimension_accuracies)
stats_df = stats_df.sort_values('accuracy', ascending=False)
stats_df.to_csv(output_dir / 'statistics.csv', index=False)
print(f"✓ Saved: statistics.csv")

# Save full results to CSV
df.to_csv(output_dir / 'full_results.csv', index=False)
print(f"✓ Saved: full_results.csv")

print()
print("=" * 80)
print("Analysis complete! All visualizations and statistics saved.")
print("=" * 80)


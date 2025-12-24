#!/usr/bin/env python3
"""
Compare Qwen2-VL-7B-Instruct vs BLIP2-Flan-T5-xl results
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)

# Load results
qwen_stats = pd.read_csv("/home/stefano/memes/semantic-memes/output_reversed/qa-test-huawei/results/Qwen2-VL-7B-Instruct/statistics.csv")
blip_stats = pd.read_csv("/home/stefano/memes/semantic-memes/output_reversed/qa-test-huawei/results/BLIP2-Flan-T5-xl/statistics.csv")

# Add model name
qwen_stats['model'] = 'Qwen2-VL-7B-Instruct'
blip_stats['model'] = 'BLIP2-Flan-T5-xl'

# Combine
comparison = pd.concat([qwen_stats, blip_stats], ignore_index=True)

# Create comparison visualization
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

# 1. Side-by-side accuracy comparison
models = ['Qwen2-VL-7B-Instruct', 'BLIP2-Flan-T5-xl']
accuracies = [
    qwen_stats['accuracy'].iloc[0],
    blip_stats['accuracy'].iloc[0]
]
colors = ['#2ecc71' if acc >= 70 else '#f39c12' if acc >= 50 else '#e74c3c' for acc in accuracies]

bars = ax1.bar(models, accuracies, color=colors, alpha=0.8, width=0.6)
ax1.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
ax1.set_title('Model Comparison: Overall Accuracy', fontsize=14, fontweight='bold')
ax1.set_ylim(0, 100)
ax1.grid(axis='y', alpha=0.3)

# Add value labels
for i, (bar, acc) in enumerate(zip(bars, accuracies)):
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
             f'{acc:.2f}%',
             ha='center', va='bottom', fontsize=12, fontweight='bold')

# 2. Detailed comparison with correct/total
x = range(len(models))
width = 0.35

qwen_correct = qwen_stats['correct'].iloc[0]
qwen_total = qwen_stats['total'].iloc[0]
blip_correct = blip_stats['correct'].iloc[0]
blip_total = blip_stats['total'].iloc[0]

ax2.bar([x[0] - width/2], [qwen_correct], width, label='Correct', color='#2ecc71', alpha=0.8)
ax2.bar([x[0] - width/2], [qwen_total - qwen_correct], width, bottom=[qwen_correct], 
        label='Incorrect', color='#e74c3c', alpha=0.8)
ax2.bar([x[1] + width/2], [blip_correct], width, color='#2ecc71', alpha=0.8)
ax2.bar([x[1] + width/2], [blip_total - blip_correct], width, bottom=[blip_correct], 
        color='#e74c3c', alpha=0.8)

ax2.set_ylabel('Number of Questions', fontsize=12, fontweight='bold')
ax2.set_title('Model Comparison: Correct vs Incorrect Answers', fontsize=14, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels(models)
ax2.legend()
ax2.grid(axis='y', alpha=0.3)

# Add labels
ax2.text(x[0], qwen_total/2, f'{qwen_correct}/{qwen_total}\n({qwen_stats["accuracy"].iloc[0]:.1f}%)',
         ha='center', va='center', fontsize=11, fontweight='bold', color='white')
ax2.text(x[1], blip_total/2, f'{blip_correct}/{blip_total}\n({blip_stats["accuracy"].iloc[0]:.1f}%)',
         ha='center', va='center', fontsize=11, fontweight='bold', color='white')

plt.tight_layout()
output_dir = Path("/home/stefano/memes/semantic-memes/output_reversed/qa-test-huawei/results")
plt.savefig(output_dir / 'model_comparison.png', dpi=300, bbox_inches='tight')
print(f"✓ Saved: model_comparison.png")
plt.close()

# Print summary
print("=" * 80)
print("Model Comparison Summary")
print("=" * 80)
print()
print(f"{'Model':<30} {'Accuracy':<15} {'Correct/Total':<15} {'Difference':<15}")
print("-" * 80)
print(f"{'Qwen2-VL-7B-Instruct':<30} {qwen_stats['accuracy'].iloc[0]:>6.2f}%      {qwen_correct:>3}/{qwen_total:<3}        {'Baseline':<15}")
print(f"{'BLIP2-Flan-T5-xl':<30} {blip_stats['accuracy'].iloc[0]:>6.2f}%      {blip_correct:>3}/{blip_total:<3}        {blip_stats['accuracy'].iloc[0] - qwen_stats['accuracy'].iloc[0]:>+6.2f}%")
print()
print(f"Performance Gap: {qwen_stats['accuracy'].iloc[0] - blip_stats['accuracy'].iloc[0]:.2f} percentage points")
print("=" * 80)









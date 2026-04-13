#!/usr/bin/env python3
"""
Visualization Script for Futoshiki Experiment Results

This script creates various charts and graphs to compare algorithm performance.

Usage:
    python visualize_experiments.py
    python visualize_experiments.py --input experiment.csv
    python visualize_experiments.py --output charts/
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from matplotlib.colors import LogNorm

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10


def load_data(csv_path: Path) -> pd.DataFrame:
    """Load experiment CSV data."""
    print(f"Loading data from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Filter only solved puzzles for most comparisons
    df_solved = df[df['solution_found'] == True].copy()
    
    print(f"Total experiments: {len(df)}")
    print(f"Solved: {len(df_solved)}")
    print(f"Failed: {len(df) - len(df_solved)}")
    print()
    
    return df, df_solved

def maybe_log_scale(ax, values, axis='x', threshold=100):
    values = [v for v in values if v is not None]
    
    if len(values) == 0:
        return False

    min_val = max(min(values), 1e-9)  # avoid log(0)
    max_val = max(values)

    ratio = max_val / min_val

    if ratio >= threshold:
        if axis == 'x':
            ax.set_xscale('log')
        elif axis == 'y':
            ax.set_yscale('log')
        return True

    return False


def plot_time_comparison(df: pd.DataFrame, output_dir: Path):
    """Compare average time by algorithm."""
    print("Creating time comparison chart...")
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Average time by algorithm
    avg_time = df.groupby('algorithm')['time_ms'].mean().sort_values()
    colors = sns.color_palette("husl", len(avg_time))
    
    avg_time.plot(kind='bar', ax=ax1, color=colors)
    ax1.set_title('Average Time by Algorithm', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Algorithm')
    ax1.set_ylabel('Average Time (ms)')
    ax1.tick_params(axis='x', rotation=45)
    ax1.grid(axis='y', alpha=0.3)
    is_log = maybe_log_scale(ax1, avg_time.values, axis='y')

    if is_log:
        ax1.set_title('Average Time by Algorithm (log scale)', fontsize=14, fontweight='bold')

    # Add values on bars
    for i, v in enumerate(avg_time):
        ax1.text(i, v + max(avg_time)*0.02, f'{v:.1f}ms', 
                ha='center', va='bottom', fontsize=9)
    
    # Box plot
    sns.boxplot(data=df, x='algorithm', y='time_ms', ax=ax2, 
                hue='algorithm', palette="Set2", legend=False)
    ax2.set_title('Time Distribution by Algorithm', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Algorithm')
    ax2.set_ylabel('Time (ms)')
    ax2.tick_params(axis='x', rotation=45)
    ax2.set_yscale('log')
    
    plt.tight_layout()
    output_path = output_dir / 'time_comparison.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✓ Saved to {output_path}")
    plt.close()


def plot_nodes_comparison(df: pd.DataFrame, output_dir: Path):
    """Compare nodes explored by algorithm."""
    print("Creating nodes comparison chart...")
    
    fig, axes = plt.subplots(2, 2, figsize=(24, 12))
    
    # Average nodes explored
    avg_nodes = df.groupby('algorithm')['nodes_explored'].mean().sort_values()
    avg_nodes.plot(kind='barh', ax=axes[0, 0], color='skyblue')

    axes[0, 0].set_title('Average Nodes Explored', fontsize=12, fontweight='bold')
    axes[0, 0].set_xlabel('Average Nodes')
    axes[0, 0].grid(axis='x', alpha=0.3)

    # 👉 Apply adaptive log scale
    is_log_nodes = maybe_log_scale(axes[0, 0], avg_nodes.values, axis='x')

    if is_log_nodes:
        axes[0, 0].set_title('Average Nodes Explored (log scale)', fontsize=12, fontweight='bold')

    # 👉 Optional: value labels
    for i, v in enumerate(avg_nodes.values):
        axes[0, 0].text(v, i, f'{v:.1e}' if is_log_nodes else f'{v:.0f}',
                        va='center', fontsize=8)


    # Average nodes generated (if available)
    if 'nodes_generated' in df.columns:
        avg_gen = df.groupby('algorithm')['nodes_generated'].mean().sort_values()
        avg_gen.plot(kind='barh', ax=axes[0, 1], color='lightcoral')

        axes[0, 1].set_title('Average Nodes Generated', fontsize=12, fontweight='bold')
        axes[0, 1].set_xlabel('Average Nodes')
        axes[0, 1].grid(axis='x', alpha=0.3)

        # 👉 Apply adaptive log scale
        is_log_gen = maybe_log_scale(axes[0, 1], avg_gen.values, axis='x')

        if is_log_gen:
            axes[0, 1].set_title('Average Nodes Generated (log scale)', fontsize=12, fontweight='bold')

        # 👉 Optional: value labels
        for i, v in enumerate(avg_gen.values):
            axes[0, 1].text(v, i, f'{v:.1e}' if is_log_gen else f'{v:.0f}',
                            va='center', fontsize=8)

    else:
        axes[0, 1].text(0.5, 0.5, 'nodes_generated\nnot available',
                    ha='center', va='center', fontsize=12,
                    transform=axes[0, 1].transAxes)

        axes[0, 1].set_title('Average Nodes Generated', fontsize=12, fontweight='bold')
    
    # Box plot nodes explored
    sns.boxplot(data=df, y='algorithm', x='nodes_explored', ax=axes[1, 0], 
                hue='algorithm', palette="Set3", legend=False)
    axes[1, 0].set_title('Nodes Explored Distribution', fontsize=12, fontweight='bold')
    axes[1, 0].set_xscale('log')
    axes[1, 0].set_xlabel('Nodes Explored (log scale)')
    
    # Scatter: time vs nodes
    for algo in df['algorithm'].unique():
        data = df[df['algorithm'] == algo]
        axes[1, 1].scatter(data['nodes_explored'], data['time_ms'], 
                          label=algo, alpha=0.6, s=50)
    axes[1, 1].set_xlabel('Nodes Explored')
    axes[1, 1].set_ylabel('Time (ms)')
    axes[1, 1].set_title('Time vs Nodes Explored', fontsize=12, fontweight='bold')
    axes[1, 1].legend()
    axes[1, 1].set_xscale('log')
    axes[1, 1].set_yscale('log')
    axes[1, 1].grid(alpha=0.3)
    
    plt.tight_layout()
    output_path = output_dir / 'nodes_comparison.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✓ Saved to {output_path}")
    plt.close()


def plot_difficulty_analysis(df, output_dir):
    """Analyze performance by difficulty level."""
    print("Creating difficulty analysis chart...")

    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.4], hspace=0.4, wspace=0.3, top=0.94, bottom=0.06, left=0.08, right=0.98)

    ax1 = fig.add_subplot(gs[0, 0])  # Time
    ax2 = fig.add_subplot(gs[0, 1])  # Nodes
    ax3 = fig.add_subplot(gs[1, :])  # Heatmap (full width)

    # -------------------------
    # Prepare data
    # -------------------------
    difficulty_order = ['easy', 'medium', 'hard']
    df_sorted = df.copy()
    df_sorted['difficulty'] = pd.Categorical(
        df_sorted['difficulty'],
        categories=difficulty_order,
        ordered=True
    )

    # -------------------------
    # 1. Time by difficulty
    # -------------------------
    sns.barplot(
        data=df_sorted,
        x='difficulty',
        y='time_ms',
        hue='algorithm',
        ax=ax1,
        palette="muted"
    )

    ax1.set_title('Average Time by Difficulty', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Time (ms)')

    is_log_time = maybe_log_scale(ax1, df_sorted['time_ms'].values, axis='y')

    if is_log_time:
        ax1.set_title('Average Time by Difficulty (log scale)', fontsize=12, fontweight='bold')

    # -------------------------
    # 2. Nodes by difficulty
    # -------------------------
    sns.barplot(
        data=df_sorted,
        x='difficulty',
        y='nodes_explored',
        hue='algorithm',
        ax=ax2,
        palette="muted"
    )

    ax2.set_title('Average Nodes by Difficulty', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Nodes Explored')

    is_log_nodes = maybe_log_scale(ax2, df_sorted['nodes_explored'].values, axis='y')

    if is_log_nodes:
        ax2.set_title('Average Nodes by Difficulty (log scale)', fontsize=12, fontweight='bold')

    handles, labels = ax2.get_legend_handles_labels()

    ax1.legend().remove()
    ax2.legend().remove()

    fig.legend(
        handles, labels,
        loc='upper center',
        ncol=3,
        bbox_to_anchor=(0.5, 1.01),
        borderaxespad=1.5
    )
    # -------------------------
    # 3. Heatmap (Time)
    # -------------------------
    pivot_time = df_sorted.pivot_table(
        values='time_ms',
        index='algorithm',
        columns='difficulty',
        aggfunc='mean'
    )

    values = pivot_time.values.flatten()
    values = values[~np.isnan(values)]

    min_val = max(values.min(), 1e-9)
    max_val = values.max()
    ratio = max_val / min_val

    use_log = ratio >= 100

    if use_log:
        sns.heatmap(
            pivot_time,
            annot=True,
            fmt='.1e',
            cmap='YlOrRd',
            norm=LogNorm(vmin=min_val, vmax=max_val),
            ax=ax3
        )
    else:
        sns.heatmap(
            pivot_time,
            annot=True,
            fmt='.1f',
            cmap='YlOrRd',
            ax=ax3
        )

    title = 'Time Heatmap by Difficulty (ms, log scale)' if use_log else 'Time Heatmap by Difficulty (ms)'
    ax3.set_title(title, fontsize=12, fontweight='bold')

    # -------------------------
    # Save
    # -------------------------
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    output_path = output_dir / 'difficulty_analysis.png'
    plt.savefig(output_path, dpi=300)
    print(f"  ✓ Saved to {output_path}")
    plt.close()


def plot_size_analysis(df: pd.DataFrame, output_dir: Path):
    """Analyze performance by grid size."""
    print("Creating grid size analysis chart...")
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # Extract numeric size for sorting
    df_copy = df.copy()
    df_copy['size_num'] = df_copy['grid_size'].str.extract(r'(\d+)').astype(int)
    df_copy = df_copy.sort_values('size_num')
    
    # # Time by size
    # sns.lineplot(data=df_copy, x='grid_size', y='time_ms', hue='algorithm',
    #             marker='o', ax=axes[0, 0], palette="tab10")
    # axes[0, 0].set_title('Time by Grid Size', fontsize=12, fontweight='bold')
    # axes[0, 0].set_ylabel('Time (ms)')
    # axes[0, 0].set_yscale('log')
    # axes[0, 0].tick_params(axis='x', rotation=45)
    # axes[0, 0].legend(title='Algorithm')
    # axes[0, 0].grid(alpha=0.3)
    
    # Nodes by size
    sns.lineplot(data=df_copy, x='grid_size', y='nodes_explored', hue='algorithm',
                marker='s', ax=axes[0], palette="tab10")
    axes[0].set_title('Nodes Explored by Grid Size', fontsize=12, fontweight='bold')
    axes[0].set_ylabel('Nodes Explored')
    axes[0].set_yscale('log')
    axes[0].tick_params(axis='x', rotation=45)
    axes[0].legend(title='Algorithm')
    axes[0].grid(alpha=0.3)
    
    # # Memory by size
    # if 'memory_kb' in df_copy.columns:
    #     sns.lineplot(data=df_copy, x='grid_size', y='memory_kb', hue='algorithm',
    #                 marker='^', ax=axes[1, 0], palette="tab10")
    #     axes[1, 0].set_title('Memory Usage by Grid Size', fontsize=12, fontweight='bold')
    #     axes[1, 0].set_ylabel('Memory (KB)')
    #     axes[1, 0].tick_params(axis='x', rotation=45)
    #     axes[1, 0].legend(title='Algorithm')
    #     axes[1, 0].grid(alpha=0.3)
    
    # Scalability: size vs time ratio
    pivot_size = df_copy.pivot_table(values='time_ms', 
                                     index='algorithm', 
                                     columns='grid_size', 
                                     aggfunc='mean')
    values = pivot_size.values.flatten()
    values = values[~np.isnan(values)]

    min_val = max(values.min(), 1e-9)
    max_val = values.max()
    ratio = max_val / min_val

    use_log = ratio >= 100  # threshold

    if use_log:
        sns.heatmap(
            pivot_size,
            annot=True,
            fmt='.1e',  # scientific notation for log
            cmap='viridis',
            norm=LogNorm(vmin=min_val, vmax=max_val),
            ax=axes[1]
        )
    else:
        sns.heatmap(
            pivot_size,
            annot=True,
            fmt='.1f',
            cmap='viridis',
            ax=axes[1]
        )

    title = 'Time Heatmap by Size (ms, log scale)' if use_log else 'Time Heatmap by Size (ms)'
    axes[1].set_title(title, fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    output_path = output_dir / 'size_analysis.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✓ Saved to {output_path}")
    plt.close()


def plot_detailed_metrics(df: pd.DataFrame, output_dir: Path):
    """Plot detailed metrics like backtracks, constraint checks."""
    print("Creating detailed metrics chart...")
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # Assignments
    if 'assignments' in df.columns and df['assignments'].sum() > 0:
        avg_assign = df.groupby('algorithm')['assignments'].mean().sort_values()
        avg_assign.plot(kind='barh', ax=axes[0], color='lightgreen')

        axes[0].set_title('Average Assignments', fontsize=12, fontweight='bold')
        axes[0].set_xlabel('Assignments')
        axes[0].grid(axis='x', alpha=0.3)

        # 👉 Apply adaptive log scale
        is_log_assign = maybe_log_scale(axes[0], avg_assign.values, axis='x')

        if is_log_assign:
            axes[0].set_title('Average Assignments (log scale)', fontsize=12, fontweight='bold')

        # 👉 Optional value labels
        for i, v in enumerate(avg_assign.values):
            axes[0].text(v, i, f'{v:.1e}' if is_log_assign else f'{v:.0f}',
                        va='center', fontsize=8)


    # Backtracks
    if 'backtracks' in df.columns and df['backtracks'].sum() > 0:
        avg_back = df.groupby('algorithm')['backtracks'].mean().sort_values()
        avg_back.plot(kind='barh', ax=axes[1], color='salmon')

        axes[1].set_title('Average Backtracks', fontsize=12, fontweight='bold')
        axes[1].set_xlabel('Backtracks')
        axes[1].grid(axis='x', alpha=0.3)

        # 👉 Apply adaptive log scale
        is_log_back = maybe_log_scale(axes[1], avg_back.values, axis='x')

        if is_log_back:
            axes[1].set_title('Average Backtracks (log scale)', fontsize=12, fontweight='bold')

        # 👉 Optional value labels
        for i, v in enumerate(avg_back.values):
            axes[1].text(v, i, f'{v:.1e}' if is_log_back else f'{v:.0f}',
                        va='center', fontsize=8)
    
    # Constraint checks
    # if 'constraint_checks' in df.columns and df['constraint_checks'].sum() > 0:
    #     avg_checks = df.groupby('algorithm')['constraint_checks'].mean().sort_values()
    #     avg_checks.plot(kind='barh', ax=axes[1, 0], color='plum')
    #     axes[1, 0].set_title('Average Constraint Checks', fontsize=12, fontweight='bold')
    #     axes[1, 0].set_xlabel('Constraint Checks')
    #     axes[1, 0].grid(axis='x', alpha=0.3)
    
    # # Efficiency: time per node
    # df_copy = df.copy()
    # df_copy['time_per_node'] = df_copy['time_ms'] / (df_copy['nodes_explored'] + 1)
    # avg_efficiency = df_copy.groupby('algorithm')['time_per_node'].mean().sort_values()
    # avg_efficiency.plot(kind='barh', ax=axes[1, 1], color='gold')
    # axes[1, 1].set_title('Efficiency: Time per Node', fontsize=12, fontweight='bold')
    # axes[1, 1].set_xlabel('ms per Node')
    # axes[1, 1].grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    output_path = output_dir / 'detailed_metrics.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✓ Saved to {output_path}")
    plt.close()


def plot_summary_dashboard(df: pd.DataFrame, output_dir: Path):
    """Create a summary dashboard with key metrics."""
    print("Creating summary dashboard...")
    fig = plt.figure(figsize=(20, 20))
    gs = fig.add_gridspec(3, 3, height_ratios=[1, 2, 2], hspace=0.4, wspace=0.35, 
                         top=0.94, bottom=0.06, left=0.08, right=0.98)
    
    # Title
    fig.suptitle('Futoshiki Solver Performance Dashboard', 
                 fontsize=18, fontweight='bold')
    
    # 1. Overall winner by time
    ax1 = fig.add_subplot(gs[0, 0])
    avg_time = df.groupby('algorithm')['time_ms'].mean().sort_values()
    colors1 = sns.color_palette("RdYlGn_r", len(avg_time))
    bars1 = ax1.barh(range(len(avg_time)), avg_time.values, color=colors1)
    ax1.set_yticks(range(len(avg_time)))
    ax1.set_yticklabels(avg_time.index, fontsize=9)
    ax1.set_title('Avg Time (ms)', fontweight='bold', fontsize=11, pad=10)
    ax1.set_xlabel('Time (ms)', fontsize=9)
    ax1.grid(axis='x', alpha=0.3)
    is_log = maybe_log_scale(ax1, avg_time.values, threshold=100, axis='x')
    # Add value labels on bars
    for i, (bar, val) in enumerate(zip(bars1, avg_time.values)):
        if is_log:
            ax1.text(val, i, f' {val:.1e}', va='center', fontsize=8)
        else:
            ax1.text(val, i, f' {val:.0f}', va='center', fontsize=8)
    
    # 2. Overall winner by nodes
    ax2 = fig.add_subplot(gs[0, 1])
    avg_nodes = df.groupby('algorithm')['nodes_explored'].mean().sort_values()
    colors2 = sns.color_palette("RdYlGn_r", len(avg_nodes))
    bars2 = ax2.barh(range(len(avg_nodes)), avg_nodes.values, color=colors2)
    ax2.set_yticks(range(len(avg_nodes)))
    ax2.set_yticklabels(avg_nodes.index, fontsize=9)
    ax2.set_title('Avg Nodes Explored', fontweight='bold', fontsize=11, pad=10)
    ax2.set_xlabel('Nodes', fontsize=9)
    ax2.grid(axis='x', alpha=0.3)
    ax2.set_xscale('log')
    
    # 3. Success rate
    ax3 = fig.add_subplot(gs[0, 2])
    success = df.groupby('algorithm')['solution_found'].mean() * 100
    success_sorted = success.sort_values()
    colors3 = sns.color_palette("Greens", len(success_sorted))
    bars3 = ax3.barh(range(len(success_sorted)), success_sorted.values, color=colors3)
    ax3.set_yticks(range(len(success_sorted)))
    ax3.set_yticklabels(success_sorted.index, fontsize=9)
    ax3.set_title('Success Rate (%)', fontweight='bold', fontsize=11, pad=10)
    ax3.set_xlim(0, 105)
    ax3.set_xlabel('Success Rate (%)', fontsize=9)
    ax3.grid(axis='x', alpha=0.3)
    # Add value labels
    for i, (bar, val) in enumerate(zip(bars3, success_sorted.values)):
        ax3.text(val + 2, i, f'{val:.0f}%', va='center', fontsize=8)
    
    # 4. Performance by difficulty (time)
    ax4 = fig.add_subplot(gs[1, :])
    difficulty_order = ['easy', 'medium', 'hard']
    df_sorted = df.copy()
    df_sorted['difficulty'] = pd.Categorical(df_sorted['difficulty'], 
                                             categories=difficulty_order, 
                                             ordered=True)
    sns.boxplot(data=df_sorted, x='difficulty', y='time_ms', hue='algorithm', 
                ax=ax4, palette="Set2")
    ax4.set_title('Time Distribution by Difficulty', fontweight='bold', 
                  fontsize=12, pad=15)
    ax4.set_yscale('log')
    ax4.set_ylabel('Time (ms, log scale)', fontsize=10)
    ax4.set_xlabel('')  # Remove x-axis label to avoid overlap
    # Move legend to the right outside the plot area
    ax4.legend(title='Algorithm', bbox_to_anchor=(1.01, 1), loc='upper left', 
               fontsize=9, frameon=True, shadow=True)
    ax4.grid(axis='y', alpha=0.3)
    # Make tick labels clearer
    ax4.tick_params(axis='x', labelsize=10)
    
    # 5. Scalability by size
    ax5 = fig.add_subplot(gs[2, :])
    df_copy = df.copy()
    df_copy['size_num'] = df_copy['grid_size'].str.extract(r'(\d+)').astype(int)
    df_copy = df_copy.sort_values('size_num')
    sns.lineplot(data=df_copy, x='grid_size', y='time_ms', hue='algorithm',
                marker='o', ax=ax5, palette="tab10", linewidth=2.5, markersize=8)
    ax5.set_title('Scalability: Time by Grid Size', fontweight='bold', 
                  fontsize=12, pad=15)
    ax5.set_ylabel('Time (ms)', fontsize=10)
    ax5.set_xlabel('Grid Size', fontsize=10)
    ax5.set_yscale('log')
    ax5.tick_params(axis='x', rotation=0)
    ax5.legend(title='Algorithm', ncol=4, fontsize=9, loc='upper left')
    ax5.grid(alpha=0.3)
    
    output_path = output_dir / 'summary_dashboard.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✓ Saved to {output_path}")
    plt.close()


def print_statistics(df: pd.DataFrame):
    """Print summary statistics."""
    print("\n" + "="*70)
    print("SUMMARY STATISTICS")
    print("="*70)
    
    for algo in sorted(df['algorithm'].unique()):
        data = df[df['algorithm'] == algo]
        solved = data['solution_found'].sum()
        total = len(data)
        avg_time = data['time_ms'].mean()
        median_time = data['time_ms'].median()
        avg_nodes = data['nodes_explored'].mean()
        
        print(f"\n{algo}:")
        print(f"  Success: {solved}/{total} ({solved/total*100:.1f}%)")
        print(f"  Avg Time: {avg_time:.2f} ms (median: {median_time:.2f} ms)")
        print(f"  Avg Nodes: {avg_nodes:.0f}")
    
    print("\n" + "="*70)


def main():
    parser = argparse.ArgumentParser(
        description="Visualize Futoshiki experiment results"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("experiment.csv"),
        help="Input CSV file (default: experiment.csv)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("charts"),
        help="Output directory for charts (default: charts/)"
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show plots interactively instead of saving"
    )
    
    args = parser.parse_args()
    
    # Check input file
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)
    
    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)
    
    # Load data
    df, df_solved = load_data(args.input)
    
    if len(df) == 0:
        print("Error: No data found in CSV file")
        sys.exit(1)
    
    # Print statistics
    print_statistics(df_solved)
    print()
    
    # Generate visualizations
    print("Generating visualizations...")
    print("-" * 70)
    
    plot_summary_dashboard(df_solved, args.output)
    plot_time_comparison(df_solved, args.output)
    plot_nodes_comparison(df_solved, args.output)
    plot_difficulty_analysis(df_solved, args.output)
    plot_size_analysis(df_solved, args.output)
    plot_detailed_metrics(df_solved, args.output)
    
    print("-" * 70)
    print(f"\n✓ All visualizations saved to {args.output}/")
    print("\nGenerated files:")
    for file in sorted(args.output.glob("*.png")):
        print(f"  - {file.name}")


if __name__ == "__main__":
    main()

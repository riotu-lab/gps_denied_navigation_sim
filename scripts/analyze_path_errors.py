#!/usr/bin/env python3
"""
Path Error Analysis and Visualization Script for Academic Papers

This script analyzes MINS navigation performance data and generates publication-quality
visualizations and statistical summaries for academic research.

Usage:
    python analyze_path_errors.py [path_to_csv_file]
    
If no file is specified, it will look for the most recent CSV in the error_analysis directory.

Author: GPS-Denied Navigation Research
Date: 2025
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import argparse
import sys
from datetime import datetime
import scipy.stats as stats
from matplotlib.patches import Rectangle
import matplotlib.patches as mpatches

# Set publication-quality plotting style
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class PathErrorAnalyzer:
    def __init__(self, csv_file_path):
        """Initialize the analyzer with path error data"""
        self.csv_file = Path(csv_file_path)
        self.data = None
        self.stats_summary = {}
        self.load_data()
        
    def load_data(self):
        """Load and preprocess the path error data"""
        try:
            self.data = pd.read_csv(self.csv_file)
            print(f"Loaded {len(self.data)} data points from {self.csv_file}")
            
            # Calculate relative time from start
            self.data['relative_time'] = self.data['timestamp'] - self.data['timestamp'].min()
            
            # Calculate 3D position errors for both GT and EST
            self.data['gt_distance_from_origin'] = np.sqrt(
                self.data['gt_x']**2 + self.data['gt_y']**2 + self.data['gt_z']**2
            )
            self.data['est_distance_from_origin'] = np.sqrt(
                self.data['est_x']**2 + self.data['est_y']**2 + self.data['est_z']**2
            )
            
            # Convert orientation error from radians to degrees for easier interpretation
            self.data['orientation_error_deg'] = np.degrees(self.data['orientation_error'])
            
            print("Data preprocessing completed")
            
        except Exception as e:
            print(f"Error loading data: {e}")
            sys.exit(1)
    
    def calculate_statistics(self):
        """Calculate comprehensive statistics for the error data"""
        metrics = ['position_error', 'orientation_error', 'velocity_error', 'time_diff']
        
        self.stats_summary = {}
        
        for metric in metrics:
            if metric in self.data.columns:
                data_series = self.data[metric]
                
                self.stats_summary[metric] = {
                    'count': len(data_series),
                    'mean': data_series.mean(),
                    'median': data_series.median(),
                    'std': data_series.std(),
                    'min': data_series.min(),
                    'max': data_series.max(),
                    'q25': data_series.quantile(0.25),
                    'q75': data_series.quantile(0.75),
                    'q95': data_series.quantile(0.95),
                    'q99': data_series.quantile(0.99),
                    'rmse': np.sqrt(np.mean(data_series**2)),
                    'skewness': stats.skew(data_series),
                    'kurtosis': stats.kurtosis(data_series)
                }
        
        # Calculate trajectory statistics
        self.stats_summary['trajectory'] = {
            'total_duration': self.data['relative_time'].max(),
            'total_gt_distance': self.calculate_total_distance('gt'),
            'total_est_distance': self.calculate_total_distance('est'),
            'avg_speed_gt': self.calculate_average_speed('gt'),
            'avg_speed_est': self.calculate_average_speed('est'),
        }
        
        print("Statistical analysis completed")
    
    def calculate_total_distance(self, prefix):
        """Calculate total distance traveled for GT or EST trajectory"""
        x_col, y_col, z_col = f'{prefix}_x', f'{prefix}_y', f'{prefix}_z'
        
        distances = []
        for i in range(1, len(self.data)):
            dx = self.data[x_col].iloc[i] - self.data[x_col].iloc[i-1]
            dy = self.data[y_col].iloc[i] - self.data[y_col].iloc[i-1]
            dz = self.data[z_col].iloc[i] - self.data[z_col].iloc[i-1]
            distances.append(np.sqrt(dx**2 + dy**2 + dz**2))
        
        return sum(distances)
    
    def calculate_average_speed(self, prefix):
        """Calculate average speed for GT or EST trajectory"""
        total_distance = self.calculate_total_distance(prefix)
        total_time = self.data['relative_time'].max()
        return total_distance / total_time if total_time > 0 else 0
    
    def generate_summary_report(self, output_dir):
        """Generate a comprehensive text summary report"""
        report_file = output_dir / f"error_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("MINS PATH ERROR ANALYSIS REPORT\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Data Source: {self.csv_file}\n")
            f.write(f"Total Data Points: {len(self.data)}\n\n")
            
            # Trajectory Summary
            traj_stats = self.stats_summary['trajectory']
            f.write("TRAJECTORY SUMMARY\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total Duration: {traj_stats['total_duration']:.2f} seconds\n")
            f.write(f"Ground Truth Distance: {traj_stats['total_gt_distance']:.3f} meters\n")
            f.write(f"Estimated Distance: {traj_stats['total_est_distance']:.3f} meters\n")
            f.write(f"GT Average Speed: {traj_stats['avg_speed_gt']:.3f} m/s\n")
            f.write(f"EST Average Speed: {traj_stats['avg_speed_est']:.3f} m/s\n\n")
            
            # Error Statistics
            f.write("ERROR STATISTICS\n")
            f.write("-" * 40 + "\n")
            
            metrics_info = {
                'position_error': ('Position Error', 'meters'),
                'orientation_error': ('Orientation Error', 'radians'),
                'velocity_error': ('Velocity Error', 'm/s'),
                'time_diff': ('Time Synchronization', 'seconds')
            }
            
            for metric, (name, unit) in metrics_info.items():
                if metric in self.stats_summary:
                    stats = self.stats_summary[metric]
                    f.write(f"\n{name} ({unit}):\n")
                    f.write(f"  Mean ± Std:     {stats['mean']:.6f} ± {stats['std']:.6f}\n")
                    f.write(f"  Median:         {stats['median']:.6f}\n")
                    f.write(f"  Min/Max:        {stats['min']:.6f} / {stats['max']:.6f}\n")
                    f.write(f"  95th Percentile: {stats['q95']:.6f}\n")
                    f.write(f"  99th Percentile: {stats['q99']:.6f}\n")
                    f.write(f"  RMSE:           {stats['rmse']:.6f}\n")
                    f.write(f"  Skewness:       {stats['skewness']:.3f}\n")
                    f.write(f"  Kurtosis:       {stats['kurtosis']:.3f}\n")
            
            # Performance Assessment
            f.write("\n\nPERFORMANCE ASSESSMENT\n")
            f.write("-" * 40 + "\n")
            
            pos_mean = self.stats_summary['position_error']['mean']
            pos_std = self.stats_summary['position_error']['std']
            ori_mean = np.degrees(self.stats_summary['orientation_error']['mean'])
            
            f.write(f"Average Position Accuracy: {pos_mean:.3f} ± {pos_std:.3f} meters\n")
            f.write(f"Average Orientation Accuracy: {ori_mean:.2f} degrees\n")
            
            # Accuracy classifications
            if pos_mean < 1.0:
                accuracy_class = "High Precision"
            elif pos_mean < 5.0:
                accuracy_class = "Medium Precision"
            else:
                accuracy_class = "Low Precision"
            
            f.write(f"Accuracy Classification: {accuracy_class}\n")
            
            # Recommendations
            f.write("\n\nRECOMMENDations FOR IMPROVEMENT\n")
            f.write("-" * 40 + "\n")
            
            if pos_std > pos_mean * 0.5:
                f.write("• High position error variance detected - consider improving sensor fusion\n")
            
            if ori_mean > 10:
                f.write("• Orientation errors are significant - check IMU calibration\n")
            
            sync_stats = self.stats_summary.get('time_diff', {})
            if sync_stats.get('max', 0) > 0.05:
                f.write("• Time synchronization issues detected - verify sensor timing\n")
            
            f.write("\n" + "=" * 80 + "\n")
        
        print(f"Summary report saved to: {report_file}")
        return report_file
    
    def create_visualizations(self, output_dir):
        """Generate publication-quality visualizations"""
        
        # Set up the plotting style for academic papers
        plt.rcParams.update({
            'font.size': 12,
            'font.family': 'serif',
            'axes.linewidth': 1.5,
            'axes.spines.top': False,
            'axes.spines.right': False,
            'xtick.major.size': 5,
            'ytick.major.size': 5,
            'xtick.minor.size': 3,
            'ytick.minor.size': 3,
            'legend.frameon': True,
            'legend.shadow': True,
            'grid.alpha': 0.3
        })
        
        # 1. Time Series Plot of All Errors
        self.plot_error_timeseries(output_dir)
        
        # 2. 3D Trajectory Comparison
        self.plot_3d_trajectories(output_dir)
        
        # 3. Error Distribution Analysis
        self.plot_error_distributions(output_dir)
        
        # 4. Statistical Summary Dashboard
        self.plot_statistical_dashboard(output_dir)
        
        # 5. Position Error Heatmap
        self.plot_position_error_heatmap(output_dir)
        
        # 6. Correlation Analysis
        self.plot_correlation_analysis(output_dir)
        
        print("All visualizations generated successfully")
    
    def plot_error_timeseries(self, output_dir):
        """Plot time series of all error metrics"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('MINS Navigation Error Analysis Over Time', fontsize=16, fontweight='bold')
        
        # Position Error
        axes[0, 0].plot(self.data['relative_time'], self.data['position_error'], 
                       color='red', linewidth=1.5, alpha=0.8)
        axes[0, 0].set_title('Position Error', fontweight='bold')
        axes[0, 0].set_ylabel('Error (meters)')
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].axhline(y=self.data['position_error'].mean(), color='red', 
                          linestyle='--', alpha=0.7, label=f'Mean: {self.data["position_error"].mean():.2f}m')
        axes[0, 0].legend()
        
        # Orientation Error (in degrees)
        axes[0, 1].plot(self.data['relative_time'], self.data['orientation_error_deg'], 
                       color='blue', linewidth=1.5, alpha=0.8)
        axes[0, 1].set_title('Orientation Error', fontweight='bold')
        axes[0, 1].set_ylabel('Error (degrees)')
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].axhline(y=self.data['orientation_error_deg'].mean(), color='blue', 
                          linestyle='--', alpha=0.7, label=f'Mean: {self.data["orientation_error_deg"].mean():.2f}°')
        axes[0, 1].legend()
        
        # Velocity Error
        axes[1, 0].plot(self.data['relative_time'], self.data['velocity_error'], 
                       color='green', linewidth=1.5, alpha=0.8)
        axes[1, 0].set_title('Velocity Error', fontweight='bold')
        axes[1, 0].set_xlabel('Time (seconds)')
        axes[1, 0].set_ylabel('Error (m/s)')
        axes[1, 0].grid(True, alpha=0.3)
        axes[1, 0].axhline(y=self.data['velocity_error'].mean(), color='green', 
                          linestyle='--', alpha=0.7, label=f'Mean: {self.data["velocity_error"].mean():.3f}m/s')
        axes[1, 0].legend()
        
        # Cumulative Error
        axes[1, 1].plot(self.data['relative_time'], self.data['cumulative_error'], 
                       color='purple', linewidth=1.5, alpha=0.8)
        axes[1, 1].set_title('Cumulative Position Error', fontweight='bold')
        axes[1, 1].set_xlabel('Time (seconds)')
        axes[1, 1].set_ylabel('Error (meters)')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        output_file = output_dir / 'error_timeseries_analysis.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Error time series plot saved: {output_file}")
    
    def plot_3d_trajectories(self, output_dir):
        """Plot 3D trajectory comparison"""
        fig = plt.figure(figsize=(16, 6))
        
        # 3D trajectory plot
        ax1 = fig.add_subplot(121, projection='3d')
        
        # Ground truth trajectory
        ax1.plot(self.data['gt_x'], self.data['gt_y'], self.data['gt_z'], 
                'b-', linewidth=2, label='Ground Truth', alpha=0.8)
        
        # Estimated trajectory
        ax1.plot(self.data['est_x'], self.data['est_y'], self.data['est_z'], 
                'r-', linewidth=2, label='MINS Estimate', alpha=0.8)
        
        # Mark start and end points
        ax1.scatter(self.data['gt_x'].iloc[0], self.data['gt_y'].iloc[0], self.data['gt_z'].iloc[0], 
                   c='blue', s=100, marker='o', label='Start (GT)')
        ax1.scatter(self.data['est_x'].iloc[0], self.data['est_y'].iloc[0], self.data['est_z'].iloc[0], 
                   c='red', s=100, marker='o', label='Start (EST)')
        
        ax1.set_xlabel('X (meters)')
        ax1.set_ylabel('Y (meters)')
        ax1.set_zlabel('Z (meters)')
        ax1.set_title('3D Trajectory Comparison', fontweight='bold')
        ax1.legend()
        
        # 2D top-down view
        ax2 = fig.add_subplot(122)
        ax2.plot(self.data['gt_x'], self.data['gt_y'], 'b-', linewidth=2, 
                label='Ground Truth', alpha=0.8)
        ax2.plot(self.data['est_x'], self.data['est_y'], 'r-', linewidth=2, 
                label='MINS Estimate', alpha=0.8)
        
        # Color-code by position error
        scatter = ax2.scatter(self.data['est_x'], self.data['est_y'], 
                            c=self.data['position_error'], cmap='YlOrRd', 
                            s=30, alpha=0.6, edgecolors='black', linewidth=0.5)
        
        ax2.set_xlabel('X (meters)')
        ax2.set_ylabel('Y (meters)')
        ax2.set_title('Top-Down View with Position Error', fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        ax2.axis('equal')
        
        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax2)
        cbar.set_label('Position Error (meters)')
        
        plt.tight_layout()
        
        output_file = output_dir / 'trajectory_comparison_3d.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"3D trajectory plot saved: {output_file}")
    
    def plot_error_distributions(self, output_dir):
        """Plot error distribution analysis"""
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('Error Distribution Analysis', fontsize=16, fontweight='bold')
        
        errors = ['position_error', 'orientation_error_deg', 'velocity_error']
        error_names = ['Position Error (m)', 'Orientation Error (°)', 'Velocity Error (m/s)']
        
        for i, (error, name) in enumerate(zip(errors, error_names)):
            if error in self.data.columns:
                data_values = self.data[error]
                
                # Histogram with KDE
                axes[0, i].hist(data_values, bins=30, density=True, alpha=0.7, 
                               color='skyblue', edgecolor='black')
                
                # Overlay normal distribution
                mu, sigma = data_values.mean(), data_values.std()
                x = np.linspace(data_values.min(), data_values.max(), 100)
                axes[0, i].plot(x, stats.norm.pdf(x, mu, sigma), 'r-', linewidth=2, 
                               label=f'Normal (μ={mu:.3f}, σ={sigma:.3f})')
                
                axes[0, i].set_title(f'{name} Distribution', fontweight='bold')
                axes[0, i].set_xlabel(name)
                axes[0, i].set_ylabel('Density')
                axes[0, i].legend()
                axes[0, i].grid(True, alpha=0.3)
                
                # Q-Q plot
                stats.probplot(data_values, dist="norm", plot=axes[1, i])
                axes[1, i].set_title(f'{name} Q-Q Plot', fontweight='bold')
                axes[1, i].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        output_file = output_dir / 'error_distributions.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Error distribution plot saved: {output_file}")
    
    def plot_statistical_dashboard(self, output_dir):
        """Create a statistical summary dashboard"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Statistical Analysis Dashboard', fontsize=16, fontweight='bold')
        
        # Box plots
        error_data = [self.data['position_error'], self.data['orientation_error_deg'], 
                     self.data['velocity_error']]
        error_labels = ['Position\n(meters)', 'Orientation\n(degrees)', 'Velocity\n(m/s)']
        
        box_plot = axes[0, 0].boxplot(error_data, labels=error_labels, patch_artist=True)
        axes[0, 0].set_title('Error Distribution Box Plots', fontweight='bold')
        axes[0, 0].set_ylabel('Error Magnitude')
        axes[0, 0].grid(True, alpha=0.3)
        
        # Color the box plots
        colors = ['lightcoral', 'lightblue', 'lightgreen']
        for patch, color in zip(box_plot['boxes'], colors):
            patch.set_facecolor(color)
        
        # Error magnitude over trajectory distance
        cumulative_distance = np.cumsum([0] + [
            np.sqrt((self.data['gt_x'].iloc[i] - self.data['gt_x'].iloc[i-1])**2 + 
                   (self.data['gt_y'].iloc[i] - self.data['gt_y'].iloc[i-1])**2 + 
                   (self.data['gt_z'].iloc[i] - self.data['gt_z'].iloc[i-1])**2)
            for i in range(1, len(self.data))
        ])
        
        # Ensure arrays have same length
        if len(cumulative_distance) > len(self.data):
            cumulative_distance = cumulative_distance[:len(self.data)]
        elif len(cumulative_distance) < len(self.data):
            # Pad with the last value if needed
            last_val = cumulative_distance[-1] if len(cumulative_distance) > 0 else 0
            cumulative_distance = np.append(cumulative_distance, 
                                           [last_val] * (len(self.data) - len(cumulative_distance)))
        
        axes[0, 1].scatter(cumulative_distance, self.data['position_error'], 
                          alpha=0.6, s=20, c='red')
        axes[0, 1].set_title('Position Error vs. Distance Traveled', fontweight='bold')
        axes[0, 1].set_xlabel('Cumulative Distance (meters)')
        axes[0, 1].set_ylabel('Position Error (meters)')
        axes[0, 1].grid(True, alpha=0.3)
        
        # Error correlation heatmap
        error_cols = ['position_error', 'orientation_error', 'velocity_error', 'time_diff']
        available_cols = [col for col in error_cols if col in self.data.columns]
        
        if len(available_cols) > 1:
            corr_matrix = self.data[available_cols].corr()
            im = axes[1, 0].imshow(corr_matrix, cmap='coolwarm', aspect='auto', vmin=-1, vmax=1)
            axes[1, 0].set_xticks(range(len(available_cols)))
            axes[1, 0].set_yticks(range(len(available_cols)))
            axes[1, 0].set_xticklabels([col.replace('_', '\n') for col in available_cols], rotation=45)
            axes[1, 0].set_yticklabels([col.replace('_', '\n') for col in available_cols])
            axes[1, 0].set_title('Error Correlation Matrix', fontweight='bold')
            
            # Add correlation values
            for i in range(len(available_cols)):
                for j in range(len(available_cols)):
                    axes[1, 0].text(j, i, f'{corr_matrix.iloc[i, j]:.2f}', 
                                   ha='center', va='center', color='white' if abs(corr_matrix.iloc[i, j]) > 0.5 else 'black')
            
            plt.colorbar(im, ax=axes[1, 0])
        
        # Performance metrics summary
        metrics_text = f"""
        PERFORMANCE SUMMARY
        
        Position Error:
        • Mean: {self.stats_summary['position_error']['mean']:.3f} ± {self.stats_summary['position_error']['std']:.3f} m
        • 95th Percentile: {self.stats_summary['position_error']['q95']:.3f} m
        • RMSE: {self.stats_summary['position_error']['rmse']:.3f} m
        
        Orientation Error:
        • Mean: {np.degrees(self.stats_summary['orientation_error']['mean']):.2f}°
        • 95th Percentile: {np.degrees(self.stats_summary['orientation_error']['q95']):.2f}°
        
        Trajectory:
        • Duration: {self.stats_summary['trajectory']['total_duration']:.1f} s
        • Distance: {self.stats_summary['trajectory']['total_gt_distance']:.1f} m
        • Avg Speed: {self.stats_summary['trajectory']['avg_speed_gt']:.2f} m/s
        """
        
        axes[1, 1].text(0.05, 0.95, metrics_text, transform=axes[1, 1].transAxes, 
                       fontsize=11, verticalalignment='top', fontfamily='monospace',
                       bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        axes[1, 1].set_xlim(0, 1)
        axes[1, 1].set_ylim(0, 1)
        axes[1, 1].axis('off')
        axes[1, 1].set_title('Performance Metrics', fontweight='bold')
        
        plt.tight_layout()
        
        output_file = output_dir / 'statistical_dashboard.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Statistical dashboard saved: {output_file}")
    
    def plot_position_error_heatmap(self, output_dir):
        """Create a spatial heatmap of position errors"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # 2D heatmap of position errors
        scatter1 = ax1.scatter(self.data['gt_x'], self.data['gt_y'], 
                              c=self.data['position_error'], cmap='plasma', 
                              s=50, alpha=0.8, edgecolors='black', linewidth=0.5)
        ax1.set_xlabel('X Position (meters)')
        ax1.set_ylabel('Y Position (meters)')
        ax1.set_title('Position Error Spatial Distribution', fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.axis('equal')
        
        cbar1 = plt.colorbar(scatter1, ax=ax1)
        cbar1.set_label('Position Error (meters)')
        
        # Error magnitude vs. height
        scatter2 = ax2.scatter(self.data['gt_z'], self.data['position_error'], 
                              c=self.data['relative_time'], cmap='viridis', 
                              s=50, alpha=0.8, edgecolors='black', linewidth=0.5)
        ax2.set_xlabel('Z Position (meters)')
        ax2.set_ylabel('Position Error (meters)')
        ax2.set_title('Position Error vs. Height', fontweight='bold')
        ax2.grid(True, alpha=0.3)
        
        cbar2 = plt.colorbar(scatter2, ax=ax2)
        cbar2.set_label('Time (seconds)')
        
        plt.tight_layout()
        
        output_file = output_dir / 'position_error_heatmap.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Position error heatmap saved: {output_file}")
    
    def plot_correlation_analysis(self, output_dir):
        """Analyze correlations between different error metrics and trajectory features"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Error Correlation and Feature Analysis', fontsize=16, fontweight='bold')
        
        # Position error vs. orientation error
        axes[0, 0].scatter(self.data['position_error'], self.data['orientation_error_deg'], 
                          alpha=0.6, s=30, c='blue')
        axes[0, 0].set_xlabel('Position Error (meters)')
        axes[0, 0].set_ylabel('Orientation Error (degrees)')
        axes[0, 0].set_title('Position vs. Orientation Error', fontweight='bold')
        axes[0, 0].grid(True, alpha=0.3)
        
        # Add correlation coefficient
        corr_coef = np.corrcoef(self.data['position_error'], self.data['orientation_error_deg'])[0, 1]
        axes[0, 0].text(0.05, 0.95, f'Correlation: {corr_coef:.3f}', 
                       transform=axes[0, 0].transAxes, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Position error vs. speed
        if len(self.data) > 1:
            speeds = []
            for i in range(1, len(self.data)):
                dt = self.data['relative_time'].iloc[i] - self.data['relative_time'].iloc[i-1]
                if dt > 0:
                    dx = self.data['gt_x'].iloc[i] - self.data['gt_x'].iloc[i-1]
                    dy = self.data['gt_y'].iloc[i] - self.data['gt_y'].iloc[i-1]
                    dz = self.data['gt_z'].iloc[i] - self.data['gt_z'].iloc[i-1]
                    speed = np.sqrt(dx**2 + dy**2 + dz**2) / dt
                    speeds.append(speed)
                else:
                    speeds.append(0)
            
            speeds = [0] + speeds  # Add zero speed for first point
            
            axes[0, 1].scatter(speeds, self.data['position_error'], alpha=0.6, s=30, c='green')
            axes[0, 1].set_xlabel('Speed (m/s)')
            axes[0, 1].set_ylabel('Position Error (meters)')
            axes[0, 1].set_title('Position Error vs. Speed', fontweight='bold')
            axes[0, 1].grid(True, alpha=0.3)
        
        # Error evolution over time (smoothed)
        window_size = max(1, len(self.data) // 20)  # Adaptive window size
        if len(self.data) >= window_size:
            smoothed_pos_error = self.data['position_error'].rolling(window=window_size, center=True).mean()
            smoothed_ori_error = self.data['orientation_error_deg'].rolling(window=window_size, center=True).mean()
            
            axes[1, 0].plot(self.data['relative_time'], smoothed_pos_error, 
                           'red', linewidth=2, label='Position Error (smoothed)')
            axes[1, 0].set_xlabel('Time (seconds)')
            axes[1, 0].set_ylabel('Position Error (meters)', color='red')
            axes[1, 0].tick_params(axis='y', labelcolor='red')
            axes[1, 0].grid(True, alpha=0.3)
            
            ax_twin = axes[1, 0].twinx()
            ax_twin.plot(self.data['relative_time'], smoothed_ori_error, 
                        'blue', linewidth=2, label='Orientation Error (smoothed)')
            ax_twin.set_ylabel('Orientation Error (degrees)', color='blue')
            ax_twin.tick_params(axis='y', labelcolor='blue')
            
            axes[1, 0].set_title('Smoothed Error Evolution', fontweight='bold')
        
        # Distance from origin analysis
        axes[1, 1].scatter(self.data['gt_distance_from_origin'], self.data['position_error'], 
                          alpha=0.6, s=30, c='purple')
        axes[1, 1].set_xlabel('Distance from Origin (meters)')
        axes[1, 1].set_ylabel('Position Error (meters)')
        axes[1, 1].set_title('Position Error vs. Distance from Origin', fontweight='bold')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        output_file = output_dir / 'correlation_analysis.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Correlation analysis plot saved: {output_file}")

def find_latest_csv(directory):
    """Find the most recent CSV file in the specified directory"""
    csv_files = list(Path(directory).glob("*.csv"))
    if not csv_files:
        return None
    return max(csv_files, key=lambda x: x.stat().st_mtime)

def main():
    parser = argparse.ArgumentParser(description="Analyze and visualize MINS path error data")
    parser.add_argument("csv_file", nargs="?", help="Path to CSV file containing error data")
    parser.add_argument("--output-dir", "-o", default="./analysis_output", 
                       help="Output directory for generated plots and reports")
    
    args = parser.parse_args()
    
    # Determine input file
    if args.csv_file:
        csv_file = Path(args.csv_file)
    else:
        # Look for the most recent CSV in common locations
        search_dirs = [
            "/home/user/shared_volume/error_analysis/",
            "./error_analysis/",
            "."
        ]
        
        csv_file = None
        for search_dir in search_dirs:
            csv_file = find_latest_csv(search_dir)
            if csv_file:
                break
        
        if not csv_file:
            print("No CSV file specified and none found in common directories.")
            print("Please specify a CSV file path.")
            sys.exit(1)
    
    if not csv_file.exists():
        print(f"Error: CSV file not found: {csv_file}")
        sys.exit(1)
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Analyzing path error data from: {csv_file}")
    print(f"Output directory: {output_dir}")
    
    # Perform analysis
    analyzer = PathErrorAnalyzer(csv_file)
    analyzer.calculate_statistics()
    
    # Generate reports and visualizations
    report_file = analyzer.generate_summary_report(output_dir)
    analyzer.create_visualizations(output_dir)
    
    print("\n" + "="*60)
    print("ANALYSIS COMPLETE")
    print("="*60)
    print(f"Summary report: {report_file}")
    print(f"Visualizations saved in: {output_dir}")
    print("\nGenerated files:")
    for file in sorted(output_dir.glob("*")):
        print(f"  • {file.name}")

if __name__ == "__main__":
    main() 
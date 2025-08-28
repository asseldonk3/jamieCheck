#!/usr/bin/env python3
"""
Generate comprehensive PDF report from parallel analysis results
Includes detailed statistics, charts, and insights
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
    PageBreak, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.platypus.flowables import Flowable
import pandas as pd

import sys
sys.path.append(str(Path(__file__).parent.parent))
import config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChartFlowable(Flowable):
    """Custom flowable for embedding matplotlib charts"""
    
    def __init__(self, img_path, width, height):
        Flowable.__init__(self)
        self.img_path = img_path
        self.width = width
        self.height = height
    
    def draw(self):
        self.canv.drawImage(self.img_path, 0, 0, self.width, self.height)


class ComprehensiveReportGenerator:
    """Generate detailed PDF report with insights"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
        
    def setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Section header
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=20,
            leftIndent=0
        ))
        
        # Insight box
        self.styles.add(ParagraphStyle(
            name='InsightBox',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#34495e'),
            backgroundColor=colors.HexColor('#ecf0f1'),
            leftIndent=10,
            rightIndent=10,
            spaceBefore=5,
            spaceAfter=5,
            borderWidth=1,
            borderColor=colors.HexColor('#bdc3c7')
        ))
    
    def generate_charts(self, results: List[Dict], stats: Dict) -> Dict[str, str]:
        """Generate analysis charts"""
        charts = {}
        
        # 1. Winner Distribution Pie Chart
        fig, ax = plt.subplots(figsize=(8, 6))
        sizes = [stats['variant_a_wins'], stats['variant_b_wins'], stats['ties']]
        labels = [
            f"Variant A\n({stats['variant_a_wins']} wins)",
            f"Variant B\n({stats['variant_b_wins']} wins)",
            f"Ties\n({stats['ties']})"
        ]
        colors_list = ['#3498db', '#e74c3c', '#95a5a6']
        explode = (0.05, 0.05, 0)
        
        ax.pie(sizes, labels=labels, colors=colors_list, autopct='%1.1f%%',
               shadow=True, explode=explode, startangle=90)
        ax.set_title('Winner Distribution Across 200 URLs', fontsize=16, fontweight='bold')
        
        chart_path = config.RESULTS_DIR / 'winner_distribution.png'
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        charts['winner_distribution'] = str(chart_path)
        
        # 2. Duplicate Comparison Bar Chart
        fig, ax = plt.subplots(figsize=(10, 6))
        categories = ['Average Duplicates', 'Total Duplicates']
        variant_a_values = [stats['average_duplicates_a'], stats['total_duplicates_a']]
        variant_b_values = [stats['average_duplicates_b'], stats['total_duplicates_b']]
        
        x = range(len(categories))
        width = 0.35
        
        bars1 = ax.bar([i - width/2 for i in x], variant_a_values, width, 
                       label='Variant A (opt_seg=5)', color='#3498db')
        bars2 = ax.bar([i + width/2 for i in x], variant_b_values, width,
                       label='Variant B (opt_seg=6)', color='#e74c3c')
        
        ax.set_xlabel('Metric', fontsize=12)
        ax.set_ylabel('Count', fontsize=12)
        ax.set_title('Duplicate Product Comparison', fontsize=16, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        ax.legend()
        
        # Add value labels on bars
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.annotate(f'{height:.1f}',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),
                           textcoords="offset points",
                           ha='center', va='bottom')
        
        chart_path = config.RESULTS_DIR / 'duplicate_comparison.png'
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        charts['duplicate_comparison'] = str(chart_path)
        
        # 3. Confidence Distribution Histogram
        fig, ax = plt.subplots(figsize=(10, 6))
        confidences = [r['analysis'].get('confidence', 0.5) for r in results]
        
        ax.hist(confidences, bins=20, color='#16a085', edgecolor='black', alpha=0.7)
        ax.axvline(x=stats['average_confidence'], color='red', linestyle='--', 
                  linewidth=2, label=f'Average: {stats["average_confidence"]:.3f}')
        ax.set_xlabel('Confidence Score', fontsize=12)
        ax.set_ylabel('Number of URLs', fontsize=12)
        ax.set_title('Analysis Confidence Distribution', fontsize=16, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        chart_path = config.RESULTS_DIR / 'confidence_distribution.png'
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        charts['confidence_distribution'] = str(chart_path)
        
        # 4. Score Comparison Over Time
        fig, ax = plt.subplots(figsize=(12, 6))
        url_indices = [r['url_index'] for r in results[:50]]  # First 50 for clarity
        scores_a = [r['variant_a'].get('score', 0) for r in results[:50]]
        scores_b = [r['variant_b'].get('score', 0) for r in results[:50]]
        
        ax.plot(url_indices, scores_a, 'b-', label='Variant A', linewidth=2, alpha=0.7)
        ax.plot(url_indices, scores_b, 'r-', label='Variant B', linewidth=2, alpha=0.7)
        ax.fill_between(url_indices, scores_a, scores_b, 
                        where=[a > b for a, b in zip(scores_a, scores_b)],
                        color='blue', alpha=0.3, label='A Better')
        ax.fill_between(url_indices, scores_a, scores_b,
                        where=[a <= b for a, b in zip(scores_a, scores_b)],
                        color='red', alpha=0.3, label='B Better')
        
        ax.set_xlabel('URL Index', fontsize=12)
        ax.set_ylabel('Quality Score (1-10)', fontsize=12)
        ax.set_title('Quality Score Comparison (First 50 URLs)', fontsize=16, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        chart_path = config.RESULTS_DIR / 'score_progression.png'
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        charts['score_progression'] = str(chart_path)
        
        return charts
    
    def generate_executive_summary(self, stats: Dict) -> List:
        """Generate executive summary section"""
        elements = []
        
        # Title
        elements.append(Paragraph("Executive Summary", self.styles['SectionHeader']))
        elements.append(Spacer(1, 12))
        
        # Key findings
        winner_text = f"<b>Overall Winner:</b> {stats['overall_winner']}"
        elements.append(Paragraph(winner_text, self.styles['Normal']))
        elements.append(Spacer(1, 6))
        
        # Summary table
        summary_data = [
            ['Metric', 'Variant A (opt_seg=5)', 'Variant B (opt_seg=6)', 'Difference'],
            ['Win Rate', f"{stats['win_percentage_a']}%", f"{stats['win_percentage_b']}%", 
             f"{abs(stats['win_percentage_a'] - stats['win_percentage_b']):.1f}%"],
            ['Average Score', f"{stats['average_score_a']}/10", f"{stats['average_score_b']}/10",
             f"{abs(stats['average_score_a'] - stats['average_score_b']):.2f}"],
            ['Avg Duplicates', f"{stats['average_duplicates_a']:.2f}", f"{stats['average_duplicates_b']:.2f}",
             f"{abs(stats['duplicate_difference']):.2f}"],
            ['Total Duplicates', str(stats['total_duplicates_a']), str(stats['total_duplicates_b']),
             str(abs(stats['total_duplicates_a'] - stats['total_duplicates_b']))]
        ]
        
        table = Table(summary_data, colWidths=[2.5*inch, 2*inch, 2*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        # Recommendation
        rec_text = f"<b>Recommendation:</b> {stats['recommendation']}"
        elements.append(Paragraph(rec_text, self.styles['Normal']))
        
        return elements
    
    def generate_detailed_insights(self, results: List[Dict], stats: Dict) -> List:
        """Generate detailed insights section"""
        elements = []
        
        elements.append(Paragraph("Detailed Analysis Insights", self.styles['SectionHeader']))
        elements.append(Spacer(1, 12))
        
        # High confidence wins
        high_conf_a = [r for r in results if r['analysis']['winner'] == 'A' 
                      and r['analysis'].get('confidence', 0) > 0.8]
        high_conf_b = [r for r in results if r['analysis']['winner'] == 'B'
                      and r['analysis'].get('confidence', 0) > 0.8]
        
        insights = [
            f"• <b>High Confidence Wins:</b> Variant A had {len(high_conf_a)} high-confidence wins "
            f"(>80% confidence), while Variant B had {len(high_conf_b)}.",
            
            f"• <b>Duplicate Impact:</b> On average, Variant {'A' if stats['average_duplicates_a'] < stats['average_duplicates_b'] else 'B'} "
            f"shows {abs(stats['duplicate_difference']):.2f} fewer duplicate products per page, "
            f"improving product diversity.",
            
            f"• <b>Consistency:</b> With an average confidence of {stats['average_confidence']:.3f}, "
            f"the AI analysis shows {'strong' if stats['average_confidence'] > 0.7 else 'moderate'} "
            f"certainty in its assessments.",
            
            f"• <b>Quality Gap:</b> The average quality score difference of "
            f"{abs(stats['average_score_a'] - stats['average_score_b']):.2f} points suggests "
            f"{'significant' if abs(stats['average_score_a'] - stats['average_score_b']) > 1 else 'marginal'} "
            f"differences in ranking quality."
        ]
        
        for insight in insights:
            elements.append(Paragraph(insight, self.styles['Normal']))
            elements.append(Spacer(1, 8))
        
        return elements
    
    def generate_top_performers(self, results: List[Dict]) -> List:
        """Generate top performers section"""
        elements = []
        
        elements.append(Paragraph("Top Performing URLs", self.styles['SectionHeader']))
        elements.append(Spacer(1, 12))
        
        # Sort by confidence and score
        sorted_a = sorted([r for r in results if r['analysis']['winner'] == 'A'],
                         key=lambda x: (x['analysis'].get('confidence', 0), 
                                      x['variant_a'].get('score', 0)),
                         reverse=True)[:5]
        
        sorted_b = sorted([r for r in results if r['analysis']['winner'] == 'B'],
                         key=lambda x: (x['analysis'].get('confidence', 0),
                                      x['variant_b'].get('score', 0)),
                         reverse=True)[:5]
        
        # Create table for top performers
        top_data = [['URL #', 'Winner', 'Confidence', 'Score A', 'Score B', 'Key Difference']]
        
        for r in sorted_a[:3]:
            top_data.append([
                str(r['url_index']),
                'A',
                f"{r['analysis'].get('confidence', 0):.2f}",
                str(r['variant_a'].get('score', 0)),
                str(r['variant_b'].get('score', 0)),
                r['analysis'].get('key_differences', '')[:40] + '...'
            ])
        
        for r in sorted_b[:3]:
            top_data.append([
                str(r['url_index']),
                'B',
                f"{r['analysis'].get('confidence', 0):.2f}",
                str(r['variant_a'].get('score', 0)),
                str(r['variant_b'].get('score', 0)),
                r['analysis'].get('key_differences', '')[:40] + '...'
            ])
        
        table = Table(top_data, colWidths=[0.8*inch, 0.8*inch, 1*inch, 0.8*inch, 0.8*inch, 3.3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-4, -1), 'CENTER'),
            ('ALIGN', (-1, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
        ]))
        
        elements.append(table)
        
        return elements
    
    def generate_report(self, results_file: str = None, output_file: str = None):
        """Generate the complete PDF report"""
        
        # Load results
        if not results_file:
            results_file = config.RESULTS_DIR / "all_parallel_results.json"
        
        if not Path(results_file).exists():
            logger.error(f"Results file not found: {results_file}")
            return None
        
        with open(results_file, 'r') as f:
            results = json.load(f)
        
        # Load statistics
        stats_file = config.RESULTS_DIR / "parallel_statistics.json"
        if Path(stats_file).exists():
            with open(stats_file, 'r') as f:
                stats = json.load(f)
        else:
            # Calculate if not exists
            from run_parallel_analysis import calculate_final_statistics
            calculate_final_statistics(results)
            with open(stats_file, 'r') as f:
                stats = json.load(f)
        
        # Generate charts
        logger.info("Generating analysis charts...")
        charts = self.generate_charts(results, stats)
        
        # Setup PDF
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = config.BASE_DIR / f"comprehensive_report_{timestamp}.pdf"
        
        doc = SimpleDocTemplate(
            str(output_file),
            pagesize=A4,
            rightMargin=72, leftMargin=72,
            topMargin=72, bottomMargin=18
        )
        
        # Build content
        elements = []
        
        # Title page
        elements.append(Spacer(1, 2*inch))
        elements.append(Paragraph(
            "A/B Test Analysis Report",
            self.styles['CustomTitle']
        ))
        elements.append(Paragraph(
            "Comprehensive Analysis of 200 Product URLs",
            self.styles['Heading2']
        ))
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph(
            f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}",
            self.styles['Normal']
        ))
        elements.append(PageBreak())
        
        # Executive Summary
        elements.extend(self.generate_executive_summary(stats))
        elements.append(PageBreak())
        
        # Charts Section
        elements.append(Paragraph("Visual Analysis", self.styles['SectionHeader']))
        elements.append(Spacer(1, 12))
        
        # Winner distribution chart
        if 'winner_distribution' in charts:
            img = Image(charts['winner_distribution'], width=5*inch, height=3.75*inch)
            elements.append(img)
            elements.append(Spacer(1, 12))
        
        # Duplicate comparison chart
        if 'duplicate_comparison' in charts:
            img = Image(charts['duplicate_comparison'], width=5*inch, height=3*inch)
            elements.append(img)
            elements.append(PageBreak())
        
        # Confidence distribution
        if 'confidence_distribution' in charts:
            elements.append(Paragraph("Confidence Analysis", self.styles['SectionHeader']))
            elements.append(Spacer(1, 12))
            img = Image(charts['confidence_distribution'], width=5*inch, height=3*inch)
            elements.append(img)
            elements.append(Spacer(1, 12))
        
        # Score progression
        if 'score_progression' in charts:
            img = Image(charts['score_progression'], width=6*inch, height=3*inch)
            elements.append(img)
            elements.append(PageBreak())
        
        # Detailed Insights
        elements.extend(self.generate_detailed_insights(results, stats))
        elements.append(PageBreak())
        
        # Top Performers
        elements.extend(self.generate_top_performers(results))
        
        # Build PDF
        doc.build(elements)
        logger.info(f"Report generated: {output_file}")
        
        return str(output_file)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate comprehensive PDF report')
    parser.add_argument('--results', help='Path to results JSON file')
    parser.add_argument('--output', help='Output PDF file path')
    
    args = parser.parse_args()
    
    generator = ComprehensiveReportGenerator()
    report_path = generator.generate_report(
        results_file=args.results,
        output_file=args.output
    )
    
    if report_path:
        print(f"\nReport generated successfully: {report_path}")
    else:
        print("\nFailed to generate report")


if __name__ == "__main__":
    main()
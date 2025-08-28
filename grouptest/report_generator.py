"""
PDF Report Generator for A/B Test Ranking Analysis
Generates comprehensive report comparing product ranking algorithms
"""

import json
import logging
from pathlib import Path
from datetime import datetime
import sys

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, 
    Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from PIL import Image as PILImage

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import config

logger = logging.getLogger(__name__)


class ABTestReportGenerator:
    """Generate PDF reports for A/B test ranking analysis"""
    
    def __init__(self, results_file=None):
        self.results = []
        self.statistics = {}
        
        # Load results if file provided
        if results_file:
            self.load_results(results_file)
        
        # Setup styles
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Create custom styles for the report"""
        
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            textColor=colors.HexColor('#2C3E50'),
            alignment=TA_CENTER,
            spaceAfter=30
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=18,
            textColor=colors.HexColor('#34495E'),
            spaceBefore=20,
            spaceAfter=12,
            borderPadding=5,
            borderWidth=2,
            borderColor=colors.HexColor('#3498DB'),
            backColor=colors.HexColor('#ECF0F1')
        ))
        
        # Result header style
        self.styles.add(ParagraphStyle(
            name='ResultHeader',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#2C3E50'),
            spaceBefore=15,
            spaceAfter=8,
            bold=True
        ))
        
        # Analysis text style
        self.styles.add(ParagraphStyle(
            name='AnalysisText',
            parent=self.styles['Normal'],
            fontSize=11,
            alignment=TA_LEFT,
            spaceBefore=6,
            spaceAfter=6
        ))
        
        # Winner style A
        self.styles.add(ParagraphStyle(
            name='WinnerTextA',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#27AE60'),
            alignment=TA_CENTER,
            bold=True
        ))
        
        # Winner style B
        self.styles.add(ParagraphStyle(
            name='WinnerTextB',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#E74C3C'),
            alignment=TA_CENTER,
            bold=True
        ))
        
        # Winner style Tie
        self.styles.add(ParagraphStyle(
            name='WinnerTextTie',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#F39C12'),
            alignment=TA_CENTER,
            bold=True
        ))
        
        # Confidence style
        self.styles.add(ParagraphStyle(
            name='ConfidenceText',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#7F8C8D'),
            alignment=TA_LEFT
        ))
    
    def load_results(self, results_file):
        """Load analysis results from JSON file"""
        try:
            with open(results_file, 'r', encoding='utf-8') as f:
                self.results = json.load(f)
            logger.info(f"Loaded {len(self.results)} results")
            
            # Load statistics if available
            stats_file = Path(results_file).parent / "statistics.json"
            if stats_file.exists():
                with open(stats_file, 'r') as f:
                    self.statistics = json.load(f)
                logger.info("Loaded statistics")
        except Exception as e:
            logger.error(f"Failed to load results: {e}")
            raise
    
    def create_summary_section(self, story):
        """Create executive summary section"""
        
        story.append(Paragraph("Executive Summary - Product Ranking Algorithm Comparison", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Overall winner announcement with visual emphasis
        overall_winner = self.statistics.get('overall_winner', 'Unknown')
        confidence_avg = self.statistics.get('average_confidence', 0.5)
        
        if 'A' in overall_winner:
            winner_color = colors.HexColor('#27AE60')
            winner_icon = "🏆"
        elif 'B' in overall_winner:
            winner_color = colors.HexColor('#E74C3C')
            winner_icon = "🏆"
        else:
            winner_color = colors.HexColor('#F39C12')
            winner_icon = "🤝"
        
        winner_text = f"""
        <para align="center">
        <font size="20" color="#{winner_color.hexval()[2:]}"><b>{winner_icon} Overall Winner: {overall_winner}</b></font>
        </para>
        """
        story.append(Paragraph(winner_text, self.styles['Normal']))
        
        # Average confidence indicator
        confidence_text = f"""
        <para align="center">
        <font size="12" color="#7F8C8D">Average Confidence: <b>{int(confidence_avg * 100)}%</b></font>
        </para>
        """
        story.append(Paragraph(confidence_text, self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Key metrics table
        metrics_data = [
            ['Metric', 'Variant A (opt_seg=5)', 'Variant B (opt_seg=6)'],
            ['URLs Won', f"{self.statistics.get('variant_a_wins', 0)} ({self.statistics.get('win_percentage_a', 0)}%)",
             f"{self.statistics.get('variant_b_wins', 0)} ({self.statistics.get('win_percentage_b', 0)}%)"],
            ['Average Relevance Score', f"{self.statistics.get('average_score_a', 0)}/10",
             f"{self.statistics.get('average_score_b', 0)}/10"],
            ['Traffic-Weighted Score', f"{self.statistics.get('weighted_score_a', 0)}/10",
             f"{self.statistics.get('weighted_score_b', 0)}/10"],
            ['Total URLs Analyzed', str(self.statistics.get('total_urls', 0)), '']
        ]
        
        metrics_table = Table(metrics_data, colWidths=[3*inch, 2*inch, 2*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ECF0F1')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#95A5A6')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ECF0F1'), colors.white])
        ]))
        
        story.append(metrics_table)
        story.append(Spacer(1, 30))
        
        # Key insights
        story.append(Paragraph("Key Ranking Insights", self.styles['SectionHeader']))
        
        insights = []
        
        if self.statistics.get('average_score_a', 0) > self.statistics.get('average_score_b', 0):
            insights.append("• Algorithm A (opt_seg=5) consistently produces more relevant product rankings")
        else:
            insights.append("• Algorithm B (opt_seg=6) consistently produces more relevant product rankings")
        
        if abs(self.statistics.get('weighted_score_a', 0) - self.statistics.get('weighted_score_b', 0)) > 0.5:
            insights.append("• The difference is particularly pronounced on high-traffic pages")
        
        insights.append(f"• Analysis based on {self.statistics.get('total_urls', 0)} product listing pages")
        insights.append("• Rankings evaluated for relevance to user search intent (H1 titles)")
        
        for insight in insights:
            story.append(Paragraph(insight, self.styles['AnalysisText']))
        
        story.append(PageBreak())
    
    def create_detailed_comparison(self, story, result):
        """Create detailed comparison for a single URL - one per page"""
        
        # Start fresh page for each URL
        if result['url_index'] > 1:
            story.append(PageBreak())
        
        # Clean header section
        winner = result['analysis'].get('winner', 'Unknown')
        confidence = result['analysis'].get('confidence', 0.5)
        winner_score_a = result['variant_a'].get('score', 0)
        winner_score_b = result['variant_b'].get('score', 0)
        h1_title = result['variant_a'].get('h1_title', 'Unknown')
        
        # Top section with URL info
        header_table_data = [
            [f"URL #{result['url_index']}", f"Visits: {result.get('visits', 0):,}", f"Query: {h1_title}"]
        ]
        
        header_table = Table(header_table_data, colWidths=[2*inch, 2*inch, 6*inch])
        header_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('TEXTCOLOR', (1, 0), (1, 0), colors.HexColor('#7F8C8D')),
            ('FONTNAME', (2, 0), (2, 0), 'Helvetica-Oblique'),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 20))
        
        # Winner announcement - clean and prominent
        if winner == 'A':
            winner_color = '#27AE60'
            winner_text = f"✓ Winner: Variant A (opt_seg=5)"
            border_color_a = colors.HexColor('#27AE60')
            border_color_b = colors.HexColor('#E0E0E0')
            border_width_a = 3
            border_width_b = 1
        elif winner == 'B':
            winner_color = '#E74C3C'
            winner_text = f"✓ Winner: Variant B (opt_seg=6)"
            border_color_a = colors.HexColor('#E0E0E0')
            border_color_b = colors.HexColor('#E74C3C')
            border_width_a = 1
            border_width_b = 3
        elif winner == 'Tie':
            winner_color = '#F39C12'
            winner_text = f"= Tie: Both variants perform equally"
            border_color_a = colors.HexColor('#F39C12')
            border_color_b = colors.HexColor('#F39C12')
            border_width_a = 2
            border_width_b = 2
        else:
            winner_color = '#7F8C8D'
            winner_text = "Analysis pending"
            border_color_a = colors.HexColor('#E0E0E0')
            border_color_b = colors.HexColor('#E0E0E0')
            border_width_a = 1
            border_width_b = 1
        
        # Winner summary if available
        winner_summary = result['analysis'].get('winner_summary', '')
        if winner_summary and winner != 'Tie':
            winner_text += f" - {winner_summary}"
        
        # Create winner section with scores
        confidence_percent = int(confidence * 100)
        winner_data = [
            [Paragraph(f"<font size='16' color='{winner_color}'><b>{winner_text}</b></font>", self.styles['Normal'])],
            [Paragraph(f"<font size='11'>Confidence: <b>{confidence_percent}%</b> | Score A: <b>{winner_score_a}/10</b> | Score B: <b>{winner_score_b}/10</b></font>", self.styles['Normal'])]
        ]
        
        winner_table = Table(winner_data, colWidths=[10*inch])
        winner_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(winner_table)
        story.append(Spacer(1, 15))
        
        # Screenshots side by side - make them the focal point
        screenshot_a = config.SCREENSHOTS_DIR / result['variant_a']['screenshot']
        screenshot_b = config.SCREENSHOTS_DIR / result['variant_b']['screenshot']
        
        if screenshot_a.exists() and screenshot_b.exists():
            try:
                # Use PIL to get original dimensions for aspect ratio
                from PIL import Image as PILImage
                pil_img_a = PILImage.open(str(screenshot_a))
                orig_width_a, orig_height_a = pil_img_a.size
                aspect_ratio_a = orig_width_a / orig_height_a
                pil_img_a.close()
                
                # Calculate dimensions maintaining aspect ratio
                # Maximum width for each image (side by side)
                max_img_width = 5.0 * inch
                # Maximum height to fit on page
                max_img_height = 4.5 * inch
                
                # Calculate actual dimensions based on aspect ratio
                if aspect_ratio_a > (max_img_width / max_img_height):
                    # Width-constrained
                    img_width = max_img_width
                    img_height = img_width / aspect_ratio_a
                else:
                    # Height-constrained
                    img_height = max_img_height
                    img_width = img_height * aspect_ratio_a
                
                # Create images with aspect ratio preserved
                img_a = Image(str(screenshot_a), width=img_width, height=img_height, kind='proportional')
                img_b = Image(str(screenshot_b), width=img_width, height=img_height, kind='proportional')
                
                # Simple headers
                header_a = "A (opt_seg=5)"
                header_b = "B (opt_seg=6)"
                
                # Create screenshot table with winner border
                screenshot_data = [[img_a, img_b]]
                # Set column width slightly larger than image width for padding
                col_width = img_width + 0.1 * inch
                screenshot_table = Table(screenshot_data, colWidths=[col_width, col_width])
                
                # Apply border styling based on winner
                table_style = [
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 3),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]
                
                # Add colored borders for winner
                if winner == 'A':
                    table_style.extend([
                        ('BOX', (0, 0), (0, 0), border_width_a, border_color_a),
                        ('BOX', (1, 0), (1, 0), border_width_b, border_color_b),
                    ])
                elif winner == 'B':
                    table_style.extend([
                        ('BOX', (0, 0), (0, 0), border_width_a, border_color_a),
                        ('BOX', (1, 0), (1, 0), border_width_b, border_color_b),
                    ])
                else:  # Tie or unknown
                    table_style.extend([
                        ('BOX', (0, 0), (0, 0), border_width_a, border_color_a),
                        ('BOX', (1, 0), (1, 0), border_width_b, border_color_b),
                    ])
                
                screenshot_table.setStyle(TableStyle(table_style))
                story.append(screenshot_table)
                
                # Add labels below screenshots
                label_data = [[header_a, header_b]]
                label_table = Table(label_data, colWidths=[col_width, col_width])
                label_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#7F8C8D')),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                ]))
                story.append(label_table)
                
            except Exception as e:
                logger.warning(f"Could not add screenshots for URL {result['url_index']}: {e}")
        
        # Brief analysis at bottom (optional, kept minimal)
        story.append(Spacer(1, 10))
        reasoning = result['analysis'].get('reasoning', '')
        if reasoning:
            analysis_table = Table([[reasoning]], colWidths=[10*inch])
            analysis_table.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#5A6C7D')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            story.append(analysis_table)
    
    def generate_report(self, output_file=None):
        """Generate the complete PDF report"""
        
        if not self.results:
            logger.error("No results to generate report")
            return
        
        # Create output filename
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = config.BASE_DIR / f"{config.REPORT_FILENAME}_{timestamp}.pdf"
        
        # Create document in landscape orientation
        doc = SimpleDocTemplate(
            str(output_file),
            pagesize=landscape(A4),
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        # Build story
        story = []
        
        # Add title page
        story.append(Paragraph("A/B Test Product Ranking Analysis", self.styles['CustomTitle']))
        story.append(Paragraph("Comparing opt_seg=5 vs opt_seg=6 Ranking Algorithms", self.styles['Normal']))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", self.styles['Normal']))
        story.append(PageBreak())
        
        # Add executive summary
        if self.statistics:
            self.create_summary_section(story)
        
        # Add section header for detailed results
        story.append(Paragraph("Detailed URL Analysis", self.styles['SectionHeader']))
        story.append(Spacer(1, 20))
        
        # Sort results by visits (highest first) if available
        sorted_results = sorted(self.results, key=lambda x: x.get('visits', 0), reverse=True)
        
        # Add detailed comparisons - one per page
        max_detailed = min(20, len(sorted_results))  # Show top 20 most visited URLs in detail
        
        for i, result in enumerate(sorted_results[:max_detailed]):
            # Each URL gets its own page
            self.create_detailed_comparison(story, result)
        
        # Add summary table for all URLs
        if len(sorted_results) > max_detailed:
            story.append(PageBreak())
            story.append(Paragraph("Summary Table - All URLs", self.styles['SectionHeader']))
            story.append(Spacer(1, 12))
            
            summary_data = [['URL #', 'Visits', 'Winner', 'Score A', 'Score B']]
            
            for result in sorted_results:
                summary_data.append([
                    str(result['url_index']),
                    str(result.get('visits', 0)),
                    result['analysis'].get('winner', '?'),
                    str(result['variant_a'].get('score', 0)),
                    str(result['variant_b'].get('score', 0))
                ])
            
            summary_table = Table(summary_data, colWidths=[1*inch, 1*inch, 1*inch, 1*inch, 1*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#95A5A6')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ECF0F1'), colors.white])
            ]))
            
            story.append(summary_table)
        
        # Build PDF
        try:
            doc.build(story)
            logger.info(f"Report generated: {output_file}")
            return str(output_file)
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            raise


def main():
    """Generate report from existing results"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate PDF report from A/B test results')
    parser.add_argument('--results', type=str, 
                       default=str(config.RESULTS_DIR / "all_results.json"),
                       help='Path to results JSON file')
    parser.add_argument('--output', type=str, help='Output PDF file path')
    
    args = parser.parse_args()
    
    generator = ABTestReportGenerator(args.results)
    output_file = generator.generate_report(args.output)
    
    if output_file:
        print(f"Report generated: {output_file}")


if __name__ == "__main__":
    main()
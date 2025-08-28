#!/usr/bin/env python3
"""
Generate PDF report with A/B screenshots side-by-side for direct comparison
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from PIL import Image
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
    PageBreak, Image as RLImage, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas

import sys
sys.path.append(str(Path(__file__).parent.parent))
import config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SideBySideReportGenerator:
    """Generate PDF with A/B screenshots side-by-side"""
    
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
            spaceAfter=20,
            alignment=TA_CENTER
        ))
        
        # Winner style
        self.styles.add(ParagraphStyle(
            name='WinnerStyle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#27ae60'),
            spaceAfter=10,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # URL Header
        self.styles.add(ParagraphStyle(
            name='URLHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=5,
            alignment=TA_LEFT
        ))
        
        # Analysis text
        self.styles.add(ParagraphStyle(
            name='AnalysisText',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#34495e'),
            alignment=TA_LEFT,
            leftIndent=10,
            rightIndent=10
        ))
    
    def resize_image_proportional(self, img_path, max_width, max_height):
        """Resize image while maintaining aspect ratio"""
        try:
            with Image.open(img_path) as img:
                # Get original dimensions
                width, height = img.size
                
                # Calculate scale to fit within bounds
                scale = min(max_width / width, max_height / height)
                
                # Calculate new dimensions
                new_width = width * scale
                new_height = height * scale
                
                return new_width, new_height
        except Exception as e:
            logger.warning(f"Could not process image {img_path}: {e}")
            return max_width * 0.8, max_height * 0.8
    
    def create_comparison_page(self, result, page_elements):
        """Create a single page comparing A and B side-by-side"""
        elements = []
        
        # URL Header
        url_text = f"<b>URL #{result['url_index']}</b> - Visits: {result.get('visits', 0)}"
        elements.append(Paragraph(url_text, self.styles['URLHeader']))
        
        # Query/Category from URL
        url = result['original_url']
        category = url.split('/')[-2] if '/' in url else 'Unknown'
        elements.append(Paragraph(f"Category: {category}", self.styles['Normal']))
        
        # Winner announcement
        winner = result['analysis']['winner']
        confidence = result['analysis'].get('confidence', 0)
        score_a = result['variant_a'].get('score', 0)
        score_b = result['variant_b'].get('score', 0)
        
        if winner == 'A':
            winner_text = f"<b>WINNER: Variant A (opt_seg=5)</b> - Score: {score_a}/10 vs {score_b}/10 - Confidence: {confidence:.0%}"
            winner_color = colors.HexColor('#3498db')
        elif winner == 'B':
            winner_text = f"<b>WINNER: Variant B (opt_seg=6)</b> - Score: {score_b}/10 vs {score_a}/10 - Confidence: {confidence:.0%}"
            winner_color = colors.HexColor('#e74c3c')
        else:
            winner_text = f"<b>TIE</b> - Both scored {score_a}/10 - Confidence: {confidence:.0%}"
            winner_color = colors.HexColor('#95a5a6')
        
        winner_para = Paragraph(winner_text, self.styles['WinnerStyle'])
        elements.append(winner_para)
        elements.append(Spacer(1, 10))
        
        # Side-by-side screenshots
        screenshot_a = config.SCREENSHOTS_DIR / result['variant_a']['screenshot']
        screenshot_b = config.SCREENSHOTS_DIR / result['variant_b']['screenshot']
        
        # Calculate image dimensions (side-by-side on landscape)
        max_img_width = 4.8 * inch  # Half page width minus margins
        max_img_height = 5.5 * inch  # Leave room for text
        
        # Get proportional dimensions
        width_a, height_a = self.resize_image_proportional(screenshot_a, max_img_width, max_img_height)
        width_b, height_b = self.resize_image_proportional(screenshot_b, max_img_width, max_img_height)
        
        # Use the smaller height to align images
        final_height = min(height_a, height_b)
        
        # Create image table for side-by-side layout
        img_data = []
        
        # Headers
        header_a = Paragraph("<b>Variant A (opt_seg=5)</b>", self.styles['Heading3'])
        header_b = Paragraph("<b>Variant B (opt_seg=6)</b>", self.styles['Heading3'])
        img_data.append([header_a, header_b])
        
        # Images
        if screenshot_a.exists() and screenshot_b.exists():
            img_a = RLImage(str(screenshot_a), width=width_a, height=final_height, kind='proportional')
            img_b = RLImage(str(screenshot_b), width=width_b, height=final_height, kind='proportional')
            img_data.append([img_a, img_b])
        else:
            img_data.append([Paragraph("Screenshot not found", self.styles['Normal']),
                           Paragraph("Screenshot not found", self.styles['Normal'])])
        
        # Scores and duplicates
        dup_a = result['variant_a'].get('duplicates', -1)
        dup_b = result['variant_b'].get('duplicates', -1)
        
        score_text_a = f"Score: {score_a}/10 | Duplicates: {dup_a if dup_a >= 0 else 'N/A'}"
        score_text_b = f"Score: {score_b}/10 | Duplicates: {dup_b if dup_b >= 0 else 'N/A'}"
        
        img_data.append([
            Paragraph(score_text_a, self.styles['Normal']),
            Paragraph(score_text_b, self.styles['Normal'])
        ])
        
        # Create table with images
        img_table = Table(img_data, colWidths=[5*inch, 5*inch])
        
        # Style based on winner
        border_color_a = winner_color if winner == 'A' else colors.grey
        border_color_b = winner_color if winner == 'B' else colors.grey
        
        img_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 1), (0, 1), 2, border_color_a),  # Border for A
            ('GRID', (1, 1), (1, 1), 2, border_color_b),  # Border for B
            ('TOPPADDING', (0, 2), (-1, 2), 5),
            ('FONTSIZE', (0, 2), (-1, 2), 10),
        ]))
        
        elements.append(img_table)
        elements.append(Spacer(1, 10))
        
        # Key differences and reasoning
        key_diff = result['analysis'].get('key_differences', '')
        reasoning = result['analysis'].get('reasoning', '')
        
        if key_diff:
            elements.append(Paragraph("<b>Key Differences:</b>", self.styles['Normal']))
            elements.append(Paragraph(key_diff[:200] + "..." if len(key_diff) > 200 else key_diff, 
                                    self.styles['AnalysisText']))
        
        # Add page break for next comparison
        elements.append(PageBreak())
        
        return elements
    
    def generate_summary_page(self, stats):
        """Generate summary statistics page"""
        elements = []
        
        elements.append(Paragraph("Executive Summary", self.styles['CustomTitle']))
        elements.append(Spacer(1, 20))
        
        # Overall winner
        winner_text = f"<b>Overall Winner: {stats['overall_winner']}</b>"
        elements.append(Paragraph(winner_text, self.styles['WinnerStyle']))
        elements.append(Spacer(1, 15))
        
        # Statistics table
        stats_data = [
            ['Metric', 'Variant A (opt_seg=5)', 'Variant B (opt_seg=6)'],
            ['Total Wins', f"{stats['variant_a_wins']}", f"{stats['variant_b_wins']}"],
            ['Win Percentage', f"{stats['win_percentage_a']}%", f"{stats['win_percentage_b']}%"],
            ['Average Score', f"{stats['average_score_a']}/10", f"{stats['average_score_b']}/10"],
            ['Average Duplicates', f"{stats['average_duplicates_a']:.2f}", f"{stats['average_duplicates_b']:.2f}"],
            ['High Confidence Wins', f"{stats['high_confidence_wins_a']}", f"{stats['high_confidence_wins_b']}"],
        ]
        
        table = Table(stats_data, colWidths=[3*inch, 2.5*inch, 2.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        # Recommendation
        elements.append(Paragraph("<b>Recommendation:</b>", self.styles['Heading2']))
        elements.append(Paragraph(stats['recommendation'], self.styles['Normal']))
        
        elements.append(PageBreak())
        
        return elements
    
    def generate_report(self, output_file=None, limit=50):
        """Generate the side-by-side comparison report"""
        
        # Load results
        results_file = config.RESULTS_DIR / "final_200_results.json"
        if not results_file.exists():
            logger.error(f"Results file not found: {results_file}")
            return None
        
        with open(results_file, 'r') as f:
            results = json.load(f)
        
        # Load statistics
        stats_file = config.RESULTS_DIR / "final_200_statistics.json"
        with open(stats_file, 'r') as f:
            stats = json.load(f)
        
        # Setup PDF
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = config.BASE_DIR / f"sidebyside_comparison_report_{timestamp}.pdf"
        
        doc = SimpleDocTemplate(
            str(output_file),
            pagesize=landscape(A4),
            rightMargin=36, leftMargin=36,
            topMargin=36, bottomMargin=36
        )
        
        # Build content
        elements = []
        
        # Title page
        elements.append(Spacer(1, 2*inch))
        elements.append(Paragraph(
            "A/B Test Visual Comparison Report",
            self.styles['CustomTitle']
        ))
        elements.append(Paragraph(
            "Side-by-Side Analysis of opt_seg=5 vs opt_seg=6",
            self.styles['Heading2']
        ))
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph(
            f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}",
            self.styles['Normal']
        ))
        elements.append(PageBreak())
        
        # Summary page
        elements.extend(self.generate_summary_page(stats))
        
        # Filter results to show most interesting comparisons
        # Show: All wins for A, all wins for B (up to limit), and a few ties
        a_wins = [r for r in results if r['analysis']['winner'] == 'A'][:20]
        b_wins = [r for r in results if r['analysis']['winner'] == 'B'][:25]
        ties = [r for r in results if r['analysis']['winner'] == 'Tie'][:5]
        
        selected_results = a_wins + b_wins + ties
        selected_results.sort(key=lambda x: x['url_index'])
        
        # Add comparison pages
        for result in selected_results[:limit]:
            try:
                page_elements = self.create_comparison_page(result, elements)
                elements.extend(page_elements)
            except Exception as e:
                logger.warning(f"Failed to create page for URL {result.get('url_index')}: {e}")
        
        # Build PDF
        doc.build(elements)
        logger.info(f"Side-by-side report generated: {output_file}")
        
        return str(output_file)


def main():
    """Generate the side-by-side comparison report"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate side-by-side comparison PDF')
    parser.add_argument('--output', help='Output PDF file path')
    parser.add_argument('--limit', type=int, default=50, help='Maximum number of comparisons to include')
    
    args = parser.parse_args()
    
    generator = SideBySideReportGenerator()
    report_path = generator.generate_report(
        output_file=args.output,
        limit=args.limit
    )
    
    if report_path:
        print(f"\nSide-by-side report generated successfully: {report_path}")
    else:
        print("\nFailed to generate report")


if __name__ == "__main__":
    main()
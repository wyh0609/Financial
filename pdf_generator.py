# -*- coding: utf-8 -*-
import os
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 注册中文字体
def register_chinese_fonts():
    """注册中文字体，尝试多种常见字体"""
    font_paths = [
        ("SimSun", "C:/Windows/Fonts/simsun.ttc"),
        ("SimHei", "C:/Windows/Fonts/simhei.ttf"),
        ("MicrosoftYaHei", "C:/Windows/Fonts/msyh.ttc"),
        ("MicrosoftYaHeiBold", "C:/Windows/Fonts/msyhbd.ttc"),
    ]
    
    registered = {}
    for font_name, font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                registered[font_name] = font_path
            except Exception as e:
                print(f"[WARN] 注册字体 {font_name} 失败: {e}")
    
    return registered

# 全局注册字体
REGISTERED_FONTS = register_chinese_fonts()
DEFAULT_FONT = "SimSun" if "SimSun" in REGISTERED_FONTS else ("MicrosoftYaHei" if "MicrosoftYaHei" in REGISTERED_FONTS else None)
DEFAULT_FONT_BOLD = "SimHei" if "SimHei" in REGISTERED_FONTS else ("MicrosoftYaHeiBold" if "MicrosoftYaHeiBold" in REGISTERED_FONTS else DEFAULT_FONT)


def create_invest_analysis_pdf(company, year, analysis_text, output_path=None):
    """
    生成投资人分析报告PDF
    
    Args:
        company: 公司名称
        year: 年份
        analysis_text: 分析文本内容
        output_path: 输出路径，如果不指定则返回字节流
    
    Returns:
        如果 output_path 为 None，返回 PDF 字节流
        否则返回输出文件路径
    """
    if not DEFAULT_FONT:
        raise RuntimeError("未找到可用的中文字体，请确保系统安装了 simsun 或 msyh 字体")
    
    # 创建PDF文档
    if output_path:
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
    else:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
    
    # 定义样式
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'ChineseTitle',
        parent=styles['Heading1'],
        fontName=DEFAULT_FONT_BOLD,
        fontSize=20,
        leading=28,
        alignment=1,  # 居中
        spaceAfter=20,
        textColor=colors.HexColor('#1a73e8')
    )
    
    subtitle_style = ParagraphStyle(
        'ChineseSubtitle',
        parent=styles['Normal'],
        fontName=DEFAULT_FONT,
        fontSize=12,
        leading=18,
        alignment=1,  # 居中
        spaceAfter=30,
        textColor=colors.HexColor('#5f6368')
    )
    
    heading1_style = ParagraphStyle(
        'ChineseHeading1',
        parent=styles['Heading1'],
        fontName=DEFAULT_FONT_BOLD,
        fontSize=16,
        leading=24,
        spaceBefore=20,
        spaceAfter=12,
        textColor=colors.HexColor('#1a73e8'),
        borderWidth=0,
        borderColor=colors.HexColor('#1a73e8'),
        borderPadding=5,
        leftIndent=0,
        backColor=colors.HexColor('#f0f7ff')
    )
    
    heading2_style = ParagraphStyle(
        'ChineseHeading2',
        parent=styles['Heading2'],
        fontName=DEFAULT_FONT_BOLD,
        fontSize=14,
        leading=20,
        spaceBefore=15,
        spaceAfter=8,
        textColor=colors.HexColor('#188038')
    )
    
    body_style = ParagraphStyle(
        'ChineseBody',
        parent=styles['Normal'],
        fontName=DEFAULT_FONT,
        fontSize=11,
        leading=18,
        spaceAfter=8,
        firstLineIndent=22,  # 首行缩进
    )
    
    bullet_style = ParagraphStyle(
        'ChineseBullet',
        parent=styles['Normal'],
        fontName=DEFAULT_FONT,
        fontSize=11,
        leading=18,
        spaceAfter=4,
        leftIndent=22,
        bulletIndent=11,
    )
    
    # 构建PDF内容
    story = []
    
    # 标题
    story.append(Paragraph(f"{company} 投资分析报告", title_style))
    story.append(Paragraph(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}", subtitle_style))
    story.append(Spacer(1, 20))
    
    # 处理分析文本，按段落和标题解析
    lines = analysis_text.split('\n')
    current_table_data = []
    in_table = False
    
    for line in lines:
        line = line.strip()
        if not line:
            if in_table and current_table_data:
                # 结束表格
                story.append(create_table(current_table_data))
                current_table_data = []
                in_table = False
            story.append(Spacer(1, 8))
            continue
        
        # 检测表格行（包含 | 或制表符）
        if '|' in line or '\t' in line:
            if not in_table:
                in_table = True
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            if cells:
                current_table_data.append(cells)
            continue
        elif in_table:
            # 结束表格
            if current_table_data:
                story.append(create_table(current_table_data))
                current_table_data = []
            in_table = False
        
        # 检测标题
        if line.startswith('### ') or line.startswith('## ') or line.startswith('# '):
            level = line.count('#')
            text = line.replace('#', '').strip()
            if level == 1:
                story.append(Paragraph(text, heading1_style))
            else:
                story.append(Paragraph(text, heading2_style))
        elif line.startswith('**') and line.endswith('**'):
            # 粗体文本作为小标题
            text = line.replace('**', '').strip()
            story.append(Paragraph(text, heading2_style))
        elif line.startswith('- ') or line.startswith('• '):
            # 列表项
            text = line[2:].strip()
            story.append(Paragraph(f"• {text}", bullet_style))
        elif line[0].isdigit() and '. ' in line[:5]:
            # 数字列表
            story.append(Paragraph(line, bullet_style))
        else:
            # 普通段落
            story.append(Paragraph(line, body_style))
    
    # 处理未结束的表格
    if in_table and current_table_data:
        story.append(create_table(current_table_data))
    
    # 添加页脚免责声明
    story.append(Spacer(1, 30))
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontName=DEFAULT_FONT,
        fontSize=9,
        leading=14,
        textColor=colors.HexColor('#9aa0a6'),
        alignment=1,  # 居中
    )
    story.append(Paragraph("— 本报告由 AI 自动生成，仅供参考，不构成投资建议 —", disclaimer_style))
    
    # 生成PDF
    doc.build(story)
    
    if output_path:
        return output_path
    else:
        buffer.seek(0)
        return buffer.getvalue()


def create_table(data):
    """创建表格"""
    if not data or len(data) < 1:
        return Spacer(1, 8)
    
    # 确定列数
    max_cols = max(len(row) for row in data)
    
    # 统一每行的列数
    for row in data:
        while len(row) < max_cols:
            row.append('')
    
    # 创建表格
    table = Table(data, colWidths=[None]*max_cols)
    
    # 设置表格样式
    style_commands = [
        ('FONTNAME', (0, 0), (-1, -1), DEFAULT_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('LEADING', (0, 0), (-1, -1), 14),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]
    
    # 如果有表头，设置表头样式
    if len(data) > 1:
        style_commands.extend([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), DEFAULT_FONT_BOLD),
        ])
    
    table.setStyle(TableStyle(style_commands))
    return table


def generate_analysis_pdf(company, year, analysis_text):
    """
    便捷函数：生成投资分析PDF并返回字节流
    """
    return create_invest_analysis_pdf(company, year, analysis_text, output_path=None)


if __name__ == "__main__":
    # 测试
    test_text = """
# 安记食品投资分析报告

## 一、盈利能力分析

毛利率：45.2%，较上年提升2.1个百分点
净利率：12.8%，保持稳定
ROE：15.6%，高于行业平均

## 二、成长能力分析

营收增长率：18.5%
净利润增长率：22.3%

## 三、风险提示

- 原材料价格波动风险
- 市场竞争加剧风险
- 食品安全风险

## 四、投资建议

综合评级：推荐
建议买入区间：15-18元
"""
    
    pdf_bytes = generate_analysis_pdf("安记食品", "2019", test_text)
    with open("test_analysis.pdf", "wb") as f:
        f.write(pdf_bytes)
    print("测试PDF已生成: test_analysis.pdf")

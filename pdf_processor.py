# -*- coding: utf-8 -*-
import os
import json
import re
import codecs
from datetime import datetime


def parse_pdf_filename(filename):
    """解析PDF文件名，提取公司信息（UTF-8 编码处理）
    期望格式: 日期__公司全称__股票代码__公司简称__年份__报告类型.pdf
    例如: 2020-04-17__安记食品股份有限公司__603696__安记食品__2019年__年度报告.pdf
    """
    if isinstance(filename, bytes):
        filename = filename.decode('utf-8', errors='ignore')
    
    base_name = os.path.splitext(filename)[0]
    parts = base_name.split('__')
    
    if len(parts) >= 6:
        return {
            'date': parts[0],
            'company_full': parts[1],
            'stock_code': parts[2],
            'company_short': parts[3],
            'year': parts[4],
            'report_type': parts[5]
        }
    return None


def generate_txt_filename(pdf_info):
    """根据PDF信息生成对应的txt文件名"""
    if pdf_info:
        return f"{pdf_info['date']}__{pdf_info['company_full']}__{pdf_info['stock_code']}__{pdf_info['company_short']}__{pdf_info['year']}__{pdf_info['report_type']}.txt"
    return None


def pdf_to_txt_format(pdf_path, txt_path):
    """将PDF转换为与现有alltxt格式一致的txt文件（UTF-8 编码）
    
    每行格式: {"page": 页码, "allrow": 行号, "type": "text", "inside": "内容"}
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("请先安装 pdfplumber: pip install pdfplumber")
    
    results = []
    allrow = 0
    
    # 确保 PDF 路径使用 UTF-8 编码
    if isinstance(pdf_path, bytes):
        pdf_path = pdf_path.decode('utf-8', errors='ignore')
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            # 提取页面文本（pdfplumber 内部已处理编码，确保返回 UTF-8 字符串）
            text = page.extract_text()
            
            if not text:
                # 空页面
                results.append({
                    "page": page_num,
                    "allrow": allrow,
                    "type": "text",
                    "inside": ""
                })
                allrow += 1
                continue
            
            # 按行分割（统一处理换行符）
            text = text.replace('\r\n', '\n').replace('\r', '\n')
            lines = text.split('\n')
            
            for line in lines:
                # 确保每行是 UTF-8 字符串，去除不可见控制字符
                line = line.strip()
                if isinstance(line, bytes):
                    line = line.decode('utf-8', errors='ignore')
                
                # 去除不可见的控制字符（保留基本的空白字符）
                line = ''.join(ch for ch in line if ord(ch) >= 32 or ch in '\t')
                
                # 判断类型
                line_type = "text"
                if line and len(line) < 50:
                    if '目录' in line or '页' in line and '/' in line:
                        line_type = "页脚"
                    elif any(keyword in line for keyword in ['年度报告', '季度报告', '半年度报告']):
                        if len(line) < 20:
                            line_type = "页眉"
                
                results.append({
                    "page": page_num,
                    "allrow": allrow,
                    "type": line_type,
                    "inside": line
                })
                allrow += 1
    
    # 写入文件（强制 UTF-8，不转义中文）
    with open(txt_path, 'w', encoding='utf-8') as f:
        for item in results:
            # ensure_ascii=False 确保中文保留为原始字符，不转义为 \uXXXX
            line_str = json.dumps(item, ensure_ascii=False) + '\n'
            f.write(line_str)
    
    return len(results)


def process_uploaded_pdf(pdf_filename, pdf_content, allpdf_dir, alltxt_dir):
    """处理上传的PDF文件
    
    Args:
        pdf_filename: PDF文件名
        pdf_content: PDF文件内容(bytes)
        allpdf_dir: PDF存储目录
        alltxt_dir: TXT存储目录
    
    Returns:
        dict: 处理结果
    """
    # 确保目录存在
    os.makedirs(allpdf_dir, exist_ok=True)
    os.makedirs(alltxt_dir, exist_ok=True)
    
    # 解析文件名
    pdf_info = parse_pdf_filename(pdf_filename)
    if not pdf_info:
        # 文件名不符合标准格式，使用默认值
        base_name = os.path.splitext(pdf_filename)[0]
        pdf_info = {
            'date': 'unknown',
            'company_full': base_name,
            'stock_code': 'unknown',
            'company_short': base_name,
            'year': 'unknown',
            'report_type': '年度报告'
        }
        # 重新生成标准文件名
        pdf_filename = f"{pdf_info['date']}__{pdf_info['company_full']}__{pdf_info['stock_code']}__{pdf_info['company_short']}__{pdf_info['year']}__{pdf_info['report_type']}.pdf"
    
    # 保存PDF文件
    pdf_path = os.path.join(allpdf_dir, pdf_filename)
    with open(pdf_path, 'wb') as f:
        f.write(pdf_content)
    
    # 生成TXT文件名
    txt_filename = generate_txt_filename(pdf_info)
    txt_path = os.path.join(alltxt_dir, txt_filename)
    
    # 转换为TXT
    try:
        row_count = pdf_to_txt_format(pdf_path, txt_path)
        return {
            'success': True,
            'pdf_filename': pdf_filename,
            'txt_filename': txt_filename,
            'pdf_path': pdf_path,
            'txt_path': txt_path,
            'row_count': row_count,
            'company': pdf_info['company_short'],
            'year': pdf_info['year']
        }
    except Exception as e:
        # 转换失败，删除PDF
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        return {
            'success': False,
            'error': f'PDF转换失败: {str(e)}'
        }

import requests
import re
import time
from typing import List, Dict, Optional
from urllib.parse import urlparse, unquote
import html as html_module


class WebSearcher:
    """联网搜索模块：当知识库中没有公司数据时，自动搜索互联网获取信息"""
    
    HIGH_QUALITY_SOURCES = [
        'cninfo.com.cn', 'eastmoney.com', 'finance.sina.com.cn', 'stock.finance.sina.com.cn',
        '10jqka.com.cn', 'xueqiu.com', 'cls.cn', 'stcn.com', 'cs.com.cn',
        'yicai.com', 'caixin.com', 'thepaper.cn', '21jingji.com',
        'nbd.com.cn', 'zqrb.cn', 'securites.cn',
        'gsxt.gov.cn', 'tianyancha.com', 'qcc.com',
        'jrj.com.cn', 'hexun.com', 'stockstar.com.cn',
    ]
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        self.timeout = 12
    
    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        
        text = html_module.unescape(text)
        
        def replace_numeric_entity(m):
            try:
                return chr(int(m.group(1)))
            except:
                return ""
        text = re.sub(r'&#(\d+);', replace_numeric_entity, text)
        text = re.sub(r'&#[xX]([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), text)
        
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<nav[^>]*>.*?</nav>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<header[^>]*>.*?</header>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<footer[^>]*>.*?</footer>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()
        
        return text
    
    def _is_high_quality_source(self, url: str) -> bool:
        try:
            domain = urlparse(url).netloc.lower()
            for hqs in self.HIGH_QUALITY_SOURCES:
                if hqs in domain:
                    return True
        except:
            pass
        return False
    
    def _score_result(self, title: str, snippet: str, url: str, company_name: str) -> int:
        """
        对搜索结果打分（0-100），分数越高越相关
        而不是简单的通过/不通过过滤
        """
        combined = (title + " " + snippet).lower()
        company_lower = company_name.lower()
        score = 0
        
        # === 扣分项（负分）===
        
        # 明显无关的内容（重扣分）
        blocking_patterns = [
            r'字节.*是.*计算机.*存储.*单位',
            r'字节.*byte.*bit.*存储.*定义',
            r'什么是.*字节$',
            r'.*定义$',
            r'下载.*app$',
            r'招聘.*面试.*经验',
            r'薪资.*爆料.*员工',
            r'员工.*吐槽.*内幕',
            r'百科.*词条',
            r'维基百科',
            r'百度百科',
            r'知乎.*问答.*怎么$',
            r'知道\.baidu',
            r'百度文库',
            r'招聘网|job.*招聘',
            r'简历.*模板',
            r'1kb.*=.*1024',
            r'1byte.*=.*8bit',
            r'存储容量.*单位',
            r'数据存储.*最小',
            r'1024.*=.*2\^',
            r'MiB.*Mebibyte',
            r'Kibibyte.*千字节',
            r'.*blog\.csdn\.net.*article.*details',
            r'csdn\.net.*博客',
            r'cnblogs\.com.*博客园',
            r'juejin\.cn.*掘金',
            r'segmentfault.*思否',
            r'zhihu\.com.*回答',
        ]
        
        for pattern in blocking_patterns:
            if re.search(pattern, combined):
                score -= 100
                break
        
        if score < -50:
            return 0  # 直接淘汰
        
        # === 加分项 ===
        
        # 1. 包含完整公司名（最重要）
        if company_lower in combined:
            score += 40
        elif company_lower.replace("有限公司", "") in combined:
            score += 30
        elif company_lower.replace("股份有限公司", "") in combined:
            score += 30
        elif company_lower.replace("集团", "") in combined:
            score += 25
        
        # 2. 高质量财经来源
        if self._is_high_quality_source(url):
            score += 30
        
        # 3. 包含财务关键词
        financial_keywords = [
            '营收', '收入', '利润', '净利润', '盈利', '亏损',
            '资产', '负债', '财报', '年报', '业绩', '财务',
            '毛利率', '净利率', 'roe', '估值', '市值',
            '营业收入', '营业成本', '总资产', '净资产',
            '亿元', '万元', '同比增长', '增长率',
            '融资', '估值', '营收', 'GMV', 'IPO'
        ]
        fin_count = sum(1 for kw in financial_keywords if kw in combined)
        score += min(fin_count * 8, 40)
        
        # 4. 官方网站加分
        try:
            domain = urlparse(url).netloc.lower()
            if any(part in domain for part in [company_lower.replace(' ', ''), 'bytedance', 'official']):
                score += 15
        except:
            pass
        
        # 5. 标题长度合理（太短可能是垃圾）
        if 10 <= len(title) <= 80:
            score += 5
        
        # 6. 最低有效分门槛（低于15分的直接淘汰）
        final_score = max(0, min(score, 100))
        if final_score < 15:
            return 0
        
        return final_score
    
    def _extract_financial_paragraphs(self, raw_text: str, max_paragraphs: int = 5) -> str:
        if not raw_text:
            return ""
        
        lines = raw_text.split('\n')
        financial_paragraphs = []
        
        financial_indicators = [
            '营业收入', '营业成本', '净利润', '归母净利', '毛利率', '净利率',
            '总资产', '总负债', '净资产', '所有者权益', '流动资产', '流动负债',
            '货币资金', '短期借款', '存货', '应收账款', 'ROE', '资产负债率',
            '营收增长', '利润增长', '同比', '环比', '亿元', '万元',
            '每股收益', 'EPS', 'EBITDA', '经营现金流', '投资现金流',
            '融资', '估值', 'GMV', 'DAU', 'MAU'
        ]
        
        for line in lines:
            line = line.strip()
            if len(line) < 15:
                continue
            
            has_number = bool(re.search(r'\d+[\.,]?\d*(?:亿|万|%|元)?', line))
            has_indicator = any(ind in line for ind in financial_indicators)
            
            if has_number and has_indicator:
                financial_paragraphs.append(line)
                if len(financial_paragraphs) >= max_paragraphs:
                    break
        
        if financial_paragraphs:
            return '\n'.join(financial_paragraphs)
        return ""
    
    def search(self, query: str, max_results: int = 8) -> List[Dict]:
        results = []
        
        try:
            bing_results = self._search_bing(query, max_results)
            if bing_results:
                results.extend(bing_results)
        except Exception as e:
            print(f"[WebSearch] Bing搜索失败: {e}", flush=True)
        
        if not results:
            try:
                backup_results = self._search_bing_backup(query, max_results)
                if backup_results:
                    results.extend(backup_results)
            except Exception as e:
                print(f"[WebSearch] 备用搜索也失败: {e}", flush=True)
        
        print(f"[WebSearch] 搜索 '{query[:30]}...' 得到 {len(results)} 条原始结果", flush=True)
        return results[:max_results]
    
    def _search_bing(self, query: str, max_results: int = 8) -> List[Dict]:
        results = []
        
        url = "https://cn.bing.com/search"
        params = {
            'q': query,
            'setlang': 'zh-Hans',
            'count': max_results,
        }
        
        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.encoding = resp.apparent_encoding or 'utf-8'
        html = resp.text
        
        algo_blocks = re.findall(
            r'<li class="b_algo"[^>]*>.*?'
            r'<a[^>]*href="(https?://[^"]*)"[^>]*>(.*?)</a>'
            r'.*?<p[^>]*>(.*?)</p>',
            html,
            re.DOTALL | re.IGNORECASE
        )
        
        for match in algo_blocks:
            if len(match) >= 3:
                url_match = match[0]
                title_match = self._clean_text(match[1]).strip()
                snippet_match = self._clean_text(match[2]).strip()[:300]
                
                if title_match and url_match and len(title_match) > 3:
                    results.append({
                        "title": title_match,
                        "url": url_match,
                        "snippet": snippet_match,
                        "source": self._extract_domain(url_match),
                        "is_high_quality": self._is_high_quality_source(url_match)
                    })
            
            if len(results) >= max_results:
                break
        
        return results
    
    def _search_bing_backup(self, query: str, max_results: int = 8) -> List[Dict]:
        results = []
        
        url = "https://www.bing.com/search"
        params = {'q': query, 'setmkt': 'zh-CN'}
        
        resp = self.session.get(url, params=params, timeout=self.timeout + 5)
        resp.encoding = resp.apparent_encoding or 'utf-8'
        blocks = re.findall(
            r'<li class="b_algo".*?<a href="(https?://[^"]+)"[^>]*>(.+?)</a>.+?<p>(.+?)</p>',
            resp.text, re.DOTALL
        )
        
        for m in blocks:
            if len(m) >= 3:
                results.append({
                    "url": m[0],
                    "title": self._clean_text(m[1]).strip(),
                    "snippet": self._clean_text(m[2]).strip()[:300],
                    "source": self._extract_domain(m[0]),
                    "is_high_quality": self._is_high_quality_source(m[0])
                })
                
            if len(results) >= max_results:
                break
        
        return results
    
    def _extract_domain(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return "未知来源"
    
    def _fetch_page_content(self, url: str, max_length: int = 5000) -> str:
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.encoding = resp.apparent_encoding or 'utf-8'
            text = resp.text
            
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<nav[^>]*>.*?</nav>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<header[^>]*>.*?</header>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<footer[^>]*>.*?</footer>', '', text, flags=re.DOTALL | re.IGNORECASE)
            
            main_match = re.search(
                r'<(?:article|main|div)[^>]*(?:id|class)="[^"]*(?:content|article|main|body|text)[^"]*"[^>]*>(.*?)</(?:article|main|div)>',
                text, re.DOTALL | re.IGNORECASE
            )
            if main_match:
                text = main_match.group(1)
            
            content = self._clean_text(text)
            
            if len(content) > max_length:
                content = content[:max_length]
            
            return content.strip()
        except Exception as e:
            print(f"[WebSearch] 抓取页面失败 {url}: {e}", flush=True)
            return ""

    def _extract_question_keywords(self, question: str) -> str:
        """从用户问题中提取财务相关关键词，用于构建精准搜索"""
        financial_keywords = [
            '总收入', '营业收入', '营收', '收入', '净利润', '净利', '利润',
            '毛利润', '毛利率', '净利率', 'ROE', '资产', '负债', '现金流',
            '估值', '市值', '融资', 'GMV', 'DAU', 'MAU', '用户数',
            '盈利', '亏损', '增长', '同比', '营收规模', '财务数据',
            '员工人数', '薪酬', '分红', '股息', '每股收益', 'EPS',
        ]
        
        found = []
        for kw in financial_keywords:
            if kw in question:
                found.append(kw)
        
        # 也提取数字+年/季度
        year_match = re.search(r'(\d{4})\s*年?', question)
        if year_match:
            found.append(year_match.group(0))
        
        return ' '.join(found[:4]) if found else ''

    def search_company_info(self, company_name: str, year: str = "", question: str = "") -> Dict:
        """
        搜索公司信息 - 基于评分的智能版本
        使用评分系统替代硬性过滤，避免过度丢弃结果
        """
        year_suffix = f" {year}年" if year else ""
        
        # 从用户问题中提取关键词
        q_keywords = self._extract_question_keywords(question)
        
        # 搜索策略：基于用户问题动态生成搜索词
        if q_keywords:
            # 用户问了具体财务指标 → 精准搜索
            queries = [
                f'"{company_name}"{year_suffix} {q_keywords}',
                f'"{company_name}"{year_suffix} {q_keywords} 数据',
                f'{company_name}{year_suffix} {q_keywords} 具体金额 多少',
                # 备选通用搜索
                f'"{company_name}"{year_suffix} 营收 利润 财务数据',
                f'{company_name}{year_suffix} 估值 融资 经营情况',
            ]
        else:
            # 没有具体指标 → 通用财务搜索
            queries = [
                f'"{company_name}"{year_suffix} 营业收入 净利润 财务数据',
                f'"{company_name}"{year_suffix} 年报 年度报告 收入 利润',
                f'{company_name}{year_suffix} 估值 融资轮次 营收 GMV',
                f'{company_name}{year_suffix} 营收规模 盈利 亏损 财报',
                f'{company_name}{year_suffix} 公司业绩 经营情况 财务状况',
            ]
        
        if q_keywords:
            print(f"[WebSearch] 问题关键词: '{q_keywords}' → 精准搜索模式", flush=True)
        else:
            print(f"[WebSearch] 无具体关键词 → 通用搜索模式", flush=True)
        
        all_results = []
        seen_urls = set()
        
        for q in queries:
            raw_results = self.search(q, max_results=6)
            
            for r in raw_results:
                if r['url'] not in seen_urls:
                    seen_urls.add(r['url'])
                    # 给每个结果打分
                    r['relevance_score'] = self._score_result(
                        r['title'], r['snippet'], r['url'], company_name
                    )
                    all_results.append(r)
            
            time.sleep(0.2)
        
        # 按相关性评分排序（高分在前）
        all_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # 过滤掉评分为0的（被blocking_patterns完全排除的）
        valid_results = [r for r in all_results if r.get('relevance_score', 0) > 0]
        
        print(f"[WebSearch] 总结果: {len(all_results)}, 有效(评分>0): {len(valid_results)}", flush=True)
        if valid_results:
            top_scores = [(r['title'][:30], r['relevance_score']) for r in valid_results[:5]]
            for t, s in top_scores:
                print(f"  [{s}分] {t}", flush=True)
        
        # 提取高质量来源的详情页财务数据
        financial_data_parts = []
        fetch_count = 0
        
        for r in valid_results[:4]:
            if r.get('is_high_quality') and r.get('relevance_score', 0) >= 30 and fetch_count < 2:
                print(f"[WebSearch] 抓取: {r['source']} - {r['title'][:30]}...", flush=True)
                raw_content = self._fetch_page_content(r['url'], max_length=4000)
                
                if raw_content:
                    financial_text = self._extract_financial_paragraphs(raw_content, max_paragraphs=4)
                    if financial_text and len(financial_text) > 50:
                        financial_data_parts.append(
                            f"【{r['source']}】{r['title']}\n{financial_text}\n"
                        )
                        fetch_count += 1
                time.sleep(0.3)
        
        # 构建完整摘要文本 - 包含所有有效结果，供LLM分析
        summary_parts = []
        summary_parts.append(f"=== {company_name}{year_suffix} 互联网搜索结果 ===\n")
        
        # 显示所有有效结果（不截断），让LLM有充分信息
        display_results = valid_results if valid_results else all_results[:8]
        
        for i, r in enumerate(display_results, 1):
            score = r.get('relevance_score', 0)
            quality_tag = "[财经]" if r.get('is_high_quality') else ""
            
            summary_parts.append(f"[{i}] [{r['source']}] {quality_tag} (相关度:{score}分)")
            summary_parts.append(f"    标题: {r['title']}")
            if r['snippet']:
                clean_snippet = r['snippet'].replace('\n', ' ').strip()
                summary_parts.append(f"    摘要: {clean_snippet}")
            summary_parts.append("")
        
        # 扩大详情页抓取范围（高质量或高评分都抓）
        for r in valid_results[:6]:
            should_fetch = (
                (r.get('is_high_quality') and r.get('relevance_score', 0) >= 25) or
                (r.get('relevance_score', 0) >= 40)
            )
            
            if should_fetch and fetch_count < 3:
                print(f"[WebSearch] 抓取详情: {r['source']} - {r['title'][:30]}...", flush=True)
                raw_content = self._fetch_page_content(r['url'], max_length=6000)
                
                if raw_content:
                    financial_text = self._extract_financial_paragraphs(raw_content, max_paragraphs=6)
                    if financial_text and len(financial_text) > 50:
                        financial_data_parts.append(
                            f"【{r['source']}】{r['title']}\n"
                            f"URL: {r['url']}\n"
                            f"{financial_text}\n"
                        )
                        fetch_count += 1
                time.sleep(0.3)
        
        # 添加详情数据到摘要末尾
        if financial_data_parts:
            summary_parts.append("\n=== 详细页面内容 ===\n")
            summary_parts.extend(financial_data_parts)
            print(f"[WebSearch] 共抓取 {len(financial_data_parts)} 个页面详情", flush=True)
        
        # 计算整体质量
        quality_score = 0
        if valid_results:
            quality_score += min(len(valid_results) * 8, 25)
        high_quality_count = sum(1 for r in valid_results if r.get('is_high_quality'))
        quality_score += high_quality_count * 20
        if financial_data_parts:
            quality_score += 30
        # 如果有中等以上评分的结果
        if any(r.get('relevance_score', 0) >= 35 for r in valid_results):
            quality_score += 15
        
        return {
            "results": display_results,
            "all_raw_results": all_results,
            "summary_text": "\n".join(summary_parts),
            "is_web_search": True,
            "company": company_name,
            "year": year,
            "has_relevant_data": len(valid_results) > 0,
            "quality_score": quality_score,
            "has_financial_data": len(financial_data_parts) > 0,
            "financial_data_count": len(financial_data_parts),
            "high_quality_count": high_quality_count,
        }


_web_searcher_instance = None

def get_web_searcher() -> WebSearcher:
    global _web_searcher_instance
    if _web_searcher_instance is None:
        _web_searcher_instance = WebSearcher()
    return _web_searcher_instance

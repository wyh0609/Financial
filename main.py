# -*- coding: utf-8 -*-
import os
import re
import json
import glob
import time

from prompts.intent_recognition import intent_recognition_prompt
from prompts.entity_recognition import entity_recognition_prompt
from prompts.answer_generation import answer_generation_prompt
from prompts.open_question import open_question_prompt
from prompts.financial_analysis import financial_analysis_prompt
from prompts.invest_analysis import invest_analysis_raw_prompt
from prompts.career_analysis import career_analysis_raw_prompt
from prompts.web_search_answer import web_search_answer_prompt
from web_searcher import get_web_searcher


class DeepSeekApiClient:
    def __init__(self, api_key=None, base_url=None, model=None):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.base_url = base_url or os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1/chat/completions")
        self.model = model or os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
        
        import requests
        self._requests = requests
    
    def generate(self, prompt_text, max_tokens=4096, temperature=0.3):
        if hasattr(prompt_text, 'format'):
            pass
        
        text = str(prompt_text)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": text}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        print(f"[DeepSeekAPI] Requesting {self.base_url} with model {self.model}", flush=True)
        
        resp = self._requests.post(self.base_url, headers=headers, json=payload, timeout=120)
        print(f"[DeepSeekAPI] Response status: {resp.status_code}", flush=True)
        
        if resp.status_code == 200:
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        else:
            raise Exception(f"DeepSeek API error: {resp.status_code} - {resp.text[:200]}")

    def generate_stream(self, prompt_text, max_tokens=4096, temperature=0.3):
        text = str(prompt_text)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": text}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }

        print(f"[DeepSeekAPI] Streaming {self.base_url} with model {self.model}", flush=True)

        resp = self._requests.post(self.base_url, headers=headers, json=payload, timeout=120, stream=True)

        if resp.status_code != 200:
            raise Exception(f"DeepSeek API error: {resp.status_code} - {resp.text[:200]}")

        # 使用 raw 流 + 逐行解码，确保每个SSE事件立即yield不缓冲
        for raw_line in resp.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue
            line = raw_line.strip()
            if not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str.strip() == "[DONE]":
                break
            try:
                import json as _json
                chunk = _json.loads(data_str)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield content
            except Exception:
                pass


def parse_intent_recognition(response: str) -> str:
    lines = response.strip().split('\n')
    return lines[-1].strip()


def parse_entity_recognition(response: str) -> list:
    entities = []
    lines = response.strip().split('\n')
    for line in lines:
        sep = ':' if ':' in line else '：'
        if "公司名" in line:
            val = line.split(sep)[-1].strip()
            if val and val != "无":
                entities.append(val)
        if "年份" in line:
            val = line.split(sep)[-1].strip()
            if val and val != "无":
                entities.append(val)
    return entities


class ChatFinance:
    def __init__(self):
        self.llm = DeepSeekApiClient()
        
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.alltxt_dir = os.path.join(self.base_dir, "models", "alltxt")
        self.allpdf_dir = os.path.join(self.base_dir, "models", "allpdf")
        
        self._load_reports()
    
    def _load_reports(self):
        self.txt_files = {}
        self.company_names = set()
        
        if not os.path.exists(self.alltxt_dir):
            os.makedirs(self.alltxt_dir, exist_ok=True)
        
        for f in glob.glob(os.path.join(self.alltxt_dir, "*.txt")):
            fname = os.path.basename(f)
            name_no_ext = fname.replace(".txt", "")
            parts = name_no_ext.split("__")
            
            if len(parts) >= 4:
                full_company = parts[1]
                short_company = parts[3] if len(parts) > 3 else parts[1]
                year = ""
                for p in parts:
                    m = re.search(r"(\d{4})", p)
                    if m:
                        year = m.group(1)
                        break
                
                key = f"{full_company}__{short_company}__{year}" if year else f"{full_company}__{short_company}"
                self.txt_files[key] = f
                self.company_names.add(full_company)
                self.company_names.add(short_company)
        
        print(f"[OK] 财报数据已索引 ({len(self.txt_files)} 家公司)", flush=True)
    
    def reload_reports(self):
        self.txt_files = {}
        self.company_names = set()
        txt_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "alltxt")
        if os.path.exists(txt_dir):
            for filename in os.listdir(txt_dir):
                if filename.endswith(".txt"):
                    filepath = os.path.join(txt_dir, filename)
                    parts = filename.replace(".txt", "").split("__")
                    if len(parts) >= 4:
                        company_key = f"{parts[1]}__{parts[3]}"
                        year_key = parts[4] if len(parts) > 4 else ""
                        file_key = f"{company_key}__{year_key}"
                        if file_key not in self.txt_files or (year_key and year_key in filepath):
                            self.txt_files[file_key] = filepath
                        self.company_names.add(parts[1])
        print(f"[OK] 财报数据重新索引 ({len(self.txt_files)} 家公司)", flush=True)
    
    def _find_txt_file(self, entities: list) -> str:
        if not entities:
            return None
        
        company_name = entities[0] if entities else ""
        year = ""
        for e in entities[1:]:
            m = re.search(r"(\d{4})", e)
            if m:
                year = m.group(1)
                break
        
        for key, path in self.txt_files.items():
            if company_name in key:
                if year and year in key:
                    return path
                elif not year:
                    return path
        
        for key, path in self.txt_files.items():
            clean_key = key.replace("_", "")
            clean_name = company_name.replace("年", "").replace("_", "")
            if clean_name in clean_key:
                if not year or year in key:
                    return path
                return path
        
        for key, path in self.txt_files.items():
            parts = key.split("__")
            if len(parts) >= 3:
                short_name = parts[2]
                file_year = parts[3].replace("年", "") if len(parts) > 3 else ""
                if short_name in company_name or company_name in short_name:
                    if (not year or file_year == year):
                        return path
        
        return None
    
    def _read_txt_file(self, txt_path: str, max_lines: int = 500) -> str:
        lines = []
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        content = data.get("inside", "")
                        if content:
                            lines.append(content)
                    except:
                        if line and not line.startswith("{"):
                            lines.append(line)
        except Exception as e:
            print(f"[ERROR] 读取文件失败: {e}", flush=True)
        
        return "\n".join(lines)
    
    def _read_txt_file_for_finance(self, txt_path: str, max_lines: int = 5000) -> str:
        finance_keywords = [
            "营业收入", "营业成本", "净利润", "利润总额", "营业利润",
            "流动资产合计", "流动负债合计", "资产总计", "负债合计",
            "所有者权益合计", "归属于母公司所有者权益",
            "货币资金", "短期借款", "存货", "应收账款", "预付款项",
            "非经常性损益",
            "支付给职工及为职工支付的现金", "支付给职工以及为职工支付的现金",
            "在职员工的数量合计", "在职员工的数量", "母公司在职员工的数量",
            "主要子公司在职员工的数量", "当期领取薪酬员工总人数",
            "应付职工薪酬", "长期应付职工薪酬",
            "毛利率", "净利率", "资产负债率", "流动比率", "速动比率",
            "营业总收入", "营业总成本", "财务费用", "管理费用", "销售费用",
            "经营活动产生的现金流量净额", "经营活动产生的现金流量",
            "投资活动产生的现金流量净额", "筹资活动产生的现金流量净额",
            "商誉", "减值准备", "减值损失", "信用减值", "资产减值",
            "基本每股收益", "稀释每股收益", "其他综合收益",
            # 新增：估值相关字段（PE/PB计算必需）
            "总股本", "股本总额", "股份总数", "普通股股数",
            "每股净资产", "归属于母公司所有者权益合计",
            "归属于上市公司股东的净资产",
            "加权平均净资产收益率", "全面摊薄净资产收益率",
            "市盈率", "市净率", "每股经营现金流",
            "递延所得税", "应交税费", "应付账款", "预收款项",
            "资本公积", "盈余公积", "未分配利润",
            # 新增：现金流量表关键科目
            "销售商品、提供劳务收到的现金", "购买商品、接受劳务支付的现金",
            "收回投资收到的现金", "取得投资收益收到的现金",
            "购建固定资产", "偿还债务支付的现金", "分配股利",
            "现金及现金等价物", "期初现金", "期末现金",
            # 新增：资产负债表关键科目
            "应收票据", "其他应收款", "长期应收款",
            "应付票据", "合同负债", "租赁负债",
            "其他流动资产", "其他非流动资产", "投资性房地产",
            "长期股权投资", "持有至到期投资", "可供出售金融资产",
            "固定资产清理", "在建工程", "工程物资",
            "无形资产", "开发支出", "长期待摊费用", "递延所得税资产",
            "短期投资", "交易性金融资产", "衍生金融资产",
            "其他应付款", "一年内到期的非流动负债", "长期应付款",
            "专项应付款", "预计负债", "递延所得税负债", "递延收益",
            # 新增：利润表关键科目
            "营业外收入", "营业外支出", "政府补助",
            "公允价值变动收益", "公允价值变动损失",
            "资产处置收益", "资产处置损失",
            "信用减值损失", "资产减值损失",
            "利息收入", "利息支出", "汇兑收益",
            "其他收益", "其他业务收入", "其他业务成本",
            "税金及附加", "研发费用",
            # 新增：存货相关
            "存货跌价准备", "存货跌价损失", "原材料", "在产品", "产成品",
            # 新增：应收相关
            "坏账准备", "应收账款周转率", "应收账款周转天数",
            # 新增：其他重要指标
            "净资产收益率", "总资产周转率", "权益乘数",
            "利息保障倍数", "已获利息倍数", "EBITDA",
            "经营现金流", "自由现金流",
            "存货周转率", "存货周转天数",
            "总资产报酬率", "毛利率", "净利率",
        ]
        
        import re
        
        has_real_number = re.compile(r'[\d,]{4,}\.\d{2}|[\d,]{5,}|\d+\.\d+%|\d{2,}%|[\d,]{4,}\.\d')
        exclude_patterns = [
            r'^第[一二三四五六七八九十百\d]+节',
            r'^\s*第\d+章',
            r'\.{3,}\d*\s*$',
            r'^[一二三四五六七八九十]+、',
            r'^\([一二三四五六七八九十]+\)',
            r'法定代表人.*签字',
            r'签名并盖章',
            r'审计报告原件',
            r'年度报告的原稿',
            r'备查文件目录',
            r'载有公司负责人',
            r'会计师事务所.*盖章',
            r'注册会计师.*签名',
            r'保证.*年度报告.*真实.*准确.*完整',
            r'保证本年度报告中财务报告',
            r'前瞻性描述.*不构成.*承诺',
            r'实质承诺',
            r'投资者注意投资风险',
            r'是否存在被控股股东',
            r'非经营性占用资金',
            r'对外提供担保的情况',
            r'违反规定决策程序',
            r'董事无法保证',
            r'所披露年度报告的真实性',
            r'所有董事均已出席',
            r'薪酬与考核委员会.*(人数|人员构成|工作细则|召开)',
            r'薪酬政策$',
            r'薪酬体系$',
            r'薪酬激励',
            r'董事、监事、高级管理人员报酬的决策程序',
            r'董事、监事、高级管理人员报酬确定依据',
            r'短期薪酬的会计处理方法',
            r'薪酬委员会.*(委员|人数及人员构成)',
            r'年度报告全文$',
            r'^\d{4}-\d{2}-\d{2}$',
            r'^\d{4}年\d{1,2}月$',
            r'报告期内在中国证监会指定网站',
            r'在其他证券市场公布的年度报告',
            r'载有.*法定代表人.*签字',
            r'会计机构负责人.*签名并盖章',
            r'^否$',
            r'^无$',
            r'^无数据$',
        ]
        
        lines = []
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    line = line.strip()
                    if not line or len(line) < 8:
                        continue
                    try:
                        data = json.loads(line)
                        content = data.get("inside", "")
                        line_type = data.get("type", "")
                        if not content:
                            continue
                        if line_type in ("页眉", "页脚"):
                            continue
                    except:
                        content = line
                        if line.startswith("{"):
                            continue
                    
                    has_finance_kw = any(kw in content for kw in finance_keywords)
                    if not has_finance_kw:
                        continue
                    
                    excluded = False
                    for pat in exclude_patterns:
                        if re.search(pat, content):
                            excluded = True
                            break
                    
                    if excluded:
                        continue
                    
                    if has_real_number.search(content) or line_type == "excel":
                        lines.append(content)
        except Exception as e:
            print(f"[ERROR] 读取财务文件失败: {e}", flush=True)
        
        return "\n".join(lines)
    
    def _build_net_profit_trend(self, company_name: str, year: str = "") -> list:
        trend = []
        try:
            year_int = int(year) if year and year.isdigit() else 0
        except:
            year_int = 0
        
        company_files = []
        for key, path in self.txt_files.items():
            if company_name in key:
                company_files.append((key, path))
        
        if not company_files:
            return []
        
        import re as _re
        for file_key, file_path in sorted(company_files):
            file_year_match = _re.search(r'(\d{4})年?', file_key)
            if not file_year_match:
                continue
            file_year = int(file_year_match.group(1))
            
            content = self._read_txt_file(file_path, max_lines=800)
            if not content:
                continue
            
            net_profit = None
            for line in content.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if (("归属于母公司所有者的净利润" in line or "归属于上市公司股东的净利润" in line or "归属于公司普通股股东的净利润" in line or ("净利润" in line and "扣非" not in line and "少数股东" not in line and "每股" not in line and "基本" not in line and "稀释" not in line)) and "扣非" not in line and "少数股东" not in line):
                    nums = _re.findall(r'-?[\d,]+\.\d+', line)
                    for n in nums:
                        try:
                            val = float(n.replace(",", ""))
                            if abs(val) > 100000:
                                net_profit = val / 10000
                                break
                        except:
                            pass
            
            if net_profit is not None:
                trend.append({"year": file_year, "value": round(net_profit, 2)})
        
        trend.sort(key=lambda x: x["year"])
        return [item["value"] for item in trend]
    
    def _extract_per_capita_salary(self, file_content: str):
        import re as _re
        
        employee_count = None
        total_cash = None
        
        for line in file_content.split("\n"):
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            if "支付给职工及为职工支付的现金" in line or "支付给职工以及为职工支付的现金" in line:
                nums = _re.findall(r'[\d,]+\.?\d*', line)
                for n in nums:
                    try:
                        val = float(n.replace(",", ""))
                        if val > 1000000:
                            total_cash = val
                            break
                    except:
                        pass
            
            if "在职员工的数量合计" in line or "在职员工的数量" in line or "当期领取薪酬员工总人数" in line:
                nums = _re.findall(r'\b(\d{2,6})\b', line)
                for n in nums:
                    try:
                        val = int(n)
                        if 50 < val < 500000:
                            employee_count = val
                            break
                    except:
                        pass
        
        if total_cash is not None and employee_count is not None and employee_count > 0:
            salary = round(total_cash / employee_count, 2)
            if 10000 < salary < 2000000:
                return str(salary)
        
        return None
    
    def _search_local(self, company_name: str, year: str = "", max_lines: int = 500) -> list:
        results = []
        
        for key, path in self.txt_files.items():
            if company_name in key or any(c in key for c in [company_name, company_name.replace("有限公司", ""), company_name.replace("股份有限公司", "")]):
                if year and year not in key:
                    continue
                content = self._read_txt_file(path, max_lines)
                if content:
                    results.append(content)
        
        return results
    
    def ask(self, question, verbose=False, web_search=False):
        result = {
            "answer": "",
            "intent": "",
            "entities": [],
            "file": "",
            "context": [],
            "is_open": False,
            "sources": []
        }
        
        # Step 1: 意图识别
        try:
            prompt = intent_recognition_prompt(question)
            intent_response = self.llm.generate(prompt)
            intent = parse_intent_recognition(intent_response)
            result["intent"] = intent
        except Exception as e:
            if verbose:
                print(f"[意图识别] 失败: {e}", flush=True)
            intent = "检索问题"
            result["intent"] = intent
        
        # Step 2: 开放问题直接回答
        if "开放" in intent:
            result["is_open"] = True
            try:
                prompt = open_question_prompt(question)
                answer = self.llm.generate(prompt)
                result["answer"] = answer
                result["sources"].append("LLM")
            except Exception as e:
                result["answer"] = f"回答生成失败: {str(e)}"
            return result
        
        # Step 3: 实体提取
        try:
            prompt = entity_recognition_prompt(question)
            entity_response = self.llm.generate(prompt)
            entities = parse_entity_recognition(entity_response)
            result["entities"] = entities
        except Exception as e:
            if verbose:
                print(f"[实体提取] 失败: {e}", flush=True)
            entities = []
        
        if not entities:
            result["answer"] = "无法识别您问题中的公司名称，请重新描述您的问题。"
            return result
        
        company_name = entities[0]
        year = ""
        for e in entities[1:]:
            m = re.search(r"(\d{4})", e)
            if m:
                year = m.group(1)
                break
        
        # Step 4: 查找知识库文件
        txt_path = self._find_txt_file(entities)
        
        if not txt_path:
            # ===== 知识库没有该公司 =====
            if web_search:
                # 用户开启了联网 → 触发联网搜索
                if verbose:
                    print(f"[知识库] 未找到 {company_name} 的财报，启动联网搜索...", flush=True)
                
                web_data = None
                try:
                    searcher = get_web_searcher()
                    web_data = searcher.search_company_info(company_name, year, question=question)
                except Exception as e:
                    if verbose:
                        print(f"[WebSearch] 联网搜索异常: {e}", flush=True)
                
                result["sources"].append("联网搜索")
                if web_data and web_data["results"]:
                    for r in web_data["results"][:5]:
                        result["sources"].append(f"[Web] {r['source']}")
                    
                    search_summary = web_data.get("summary_text", "")
                    if search_summary:
                        if len(search_summary) > 3000:
                            search_summary = search_summary[:3000] + "\n... (内容已截断)"
                        result["context"].append(f"[联网搜索摘要]\n{search_summary}")
                    
                    quality_score = web_data.get("quality_score", 0)
                    has_financial = web_data.get("has_financial_data", False)
                    
                    if verbose:
                        print(f"[WebSearch] 质量评分: {quality_score}, 有财务数据: {has_financial}", flush=True)
                    
                    use_llm = (quality_score >= 20 and has_financial) or quality_score >= 35
                    
                    if use_llm:
                        try:
                            prompt = web_search_answer_prompt(
                                context=web_data["summary_text"],
                                question=question,
                                company=company_name
                            )
                            answer = self.llm.generate(prompt)
                            result["answer"] = answer
                            
                            if verbose:
                                print(f"[联网搜索] LLM分析完成 (质量分:{quality_score})", flush=True)
                        except Exception as llm_err:
                            if verbose:
                                print(f"[联网搜索] LLM生成失败: {llm_err}，使用降级答案", flush=True)
                            result["answer"] = self._build_fallback_answer(company_name, web_data, question)
                    else:
                        if verbose:
                            print(f"[联网搜索] 质量不足(分数:{quality_score})，使用降级答案", flush=True)
                        result["answer"] = self._build_fallback_answer(company_name, web_data, question)
                else:
                    result["answer"] = (
                        f"知识库中未找到「{company_name}」的财报数据，"
                        f"且联网搜索也未找到相关信息。\n\n"
                        f"建议您：\n1. 检查公司名称是否正确\n2. 尝试上传该公司的PDF财报文件"
                    )
                    result["sources"].append("无数据")
            else:
                # 用户未开启联网 → 提示用户
                result["sources"].append("知识库无数据")
                result["answer"] = (
                    f"本地知识库中没有「**{company_name}**」的财报数据。\n\n"
                    f"如果您想通过互联网搜索获取相关信息，请点击输入框旁边的 **「🌐 联网」** 按钮开启联网搜索功能。\n\n"
                    f"或者您可以上传该公司的 **PDF年报** 文件进行分析。"
                )
            
            return result
        
        # Step 5: 读取知识库文件内容
        result["file"] = os.path.basename(txt_path)
        file_content = self._read_txt_file(txt_path, max_lines=800)
        
        if not file_content:
            if web_search:
                try:
                    searcher = get_web_searcher()
                    web_data = searcher.search_company_info(company_name, year, question=question)
                    
                    if web_data and web_data["results"]:
                        result["sources"].append("联网搜索补充")
                        for r in web_data["results"][:5]:
                            result["sources"].append(f"[Web] {r['source']}")
                        
                        combined_context = file_content + "\n\n" + web_data["summary_text"]
                        prompt = answer_generation_prompt(combined_context, question)
                        result["answer"] = self.llm.generate(prompt)
                        return result
                except Exception as e:
                    pass
            
            result["answer"] = "[财报数据已找到，但未检索到相关内容]"
            return result
        
        # Step 6: 基于知识库内容生成答案
        result["sources"].append("知识库")
        
        import re as _re
        
        raw_lines = file_content.split("\n")
        
        def is_valid_data_line(line):
            line_stripped = line.strip()
            if not line_stripped or len(line_stripped) < 6:
                return False
            skip_patterns = [
                "词语释义", "含义如下", "下列词语", "非文义", "指，",
                "指'", "指\"", "公司全称", "公司全资子", "公司股东",
                "公司参股", "曾用名", "报告期", "中国证监会", "上交所",
                "深交所", "公司的中文名称", "公司的外文名称", "外文名称缩写",
                "法定代表人", "董事会秘书", "证券事务代表", "注册地址",
                "办公地址", "邮政编码", "公司网址", "电子信箱", "联系电话",
                "传真", "邮箱", "信息披露", "投资者关系", "联系人",
                "年度报告", "半年度报告", "季度报告", "定期报告",
                "第一节", "第二节", "第三节", "第四节", "第五节",
                "第六节", "第七节", "第八节", "第九节", "第十节",
                "第十一节", "第十二节", "第十三节", "第十四节",
                "释义", "定义", "声明", "承诺", "确认"
            ]
            for pat in skip_patterns:
                if pat in line_stripped:
                    return False
            has_number = bool(_re.search(r'[\d,]+\.?\d*%', line_stripped)) or \
                        bool(_re.search(r'[\d,]+\.\d+', line_stripped)) or \
                        bool(_re.search(r'[-]?\d[\d,]*\.\d+', line_stripped)) or \
                        bool(_re.search(r'\b\d{4}\b', line_stripped))
            if not has_number:
                return False
            if line_stripped.startswith("'") and line_stripped.count("'") == 2 and len(line_stripped) < 20:
                return False
            return True
        
        valid_lines = [line.strip() for line in raw_lines if is_valid_data_line(line)]
        
        topic_keywords = {
            "收入": ["营业收入", "营业总收入", "主营业务收入", "销售收入", "营收", "业务收入"],
            "成本": ["营业成本", "主营业务成本", "销售成本", "成本", "生产成本"],
            "利润": ["净利润", "利润总额", "营业利润", "归属于母公司", "净利", "毛利润", "利润"],
            "毛利率": ["毛利率", "毛利", "毛利润率"],
            "净利率": ["净利率", "净利润率", "净利"],
            "资产": ["资产总计", "总资产", "流动资产", "非流动资产", "固定资产", "无形资产", "资产合计"],
            "负债": ["负债合计", "总负债", "流动负债", "非流动负债", "短期借款", "长期借款", "应付", "预收"],
            "权益": ["所有者权益", "股东权益", "净资产", "归属于母公司", "实收资本", "股本"],
            "现金流": ["现金流量", "经营活动", "投资活动", "筹资活动", "现金净额", "现金流"],
            "ROE": ["ROE", "净资产收益率", "股东回报", "权益报酬"],
            "比率": ["流动比率", "速动比率", "资产负债率", "偿债能力", "比率"],
            "增长": ["增长率", "同比增长", "环比增长", "增速", "增长", "增幅"],
            "费用": ["销售费用", "管理费用", "研发费用", "财务费用", "期间费用", "费用"],
            "员工": ["员工", "职工", "薪酬", "人数", "工资"],
            "分红": ["分红", "股息", "股利", "派息"],
            "存货": ["存货", "库存"],
            "应收": ["应收账款", "应收票据", "坏账"],
            "估值": ["市盈率", "PE", "每股收益", "EPS", "每股净资产", "BPS",
                   "市净率", "PB", "总市值", "市值", "总股本", "股本总额",
                   "流通股", "非流通股", "普通股股数", "股份总数",
                   "基本每股收益", "稀释每股收益", "加权平均", "每股"],
        }
        
        q_lower = question.lower()
        matched_topics = set()
        for topic, keywords in topic_keywords.items():
            for kw in keywords:
                if kw in question:
                    matched_topics.add(topic)
                    break
        
        if not matched_topics:
            broad_keywords = ["营业收入", "营业成本", "净利润", "资产", "负债", "收入", "利润", "成本",
                            "每股收益", "市盈率", "市净率", "总股本"]
            for kw in broad_keywords:
                if kw in question:
                    break
            else:
                matched_topics = {"收入", "成本", "利润", "估值"}
        
        all_topic_keywords = set()
        for t in matched_topics:
            all_topic_keywords.update(topic_keywords.get(t, []))
        
        if matched_topics:
            filtered = []
            for line in valid_lines:
                if any(kw in line for kw in all_topic_keywords):
                    filtered.append(line)
            
            if len(filtered) >= 5:
                context_lines = filtered[:40]
            else:
                context_lines = valid_lines[:50]
        else:
            context_lines = valid_lines[:50]
        
        seen = set()
        for ctx_line in context_lines:
            if ctx_line not in seen:
                result["context"].append(ctx_line)
                seen.add(ctx_line)
        
        try:
            prompt = answer_generation_prompt(file_content, question)
            answer = self.llm.generate(prompt)
            result["answer"] = answer
        except Exception as e:
            result["answer"] = f"答案生成失败: {str(e)}"
        
        return result
    
    def ask_stream(self, question, verbose=False, web_search=False):
        result = {
            "answer": "",
            "intent": "",
            "entities": [],
            "file": "",
            "context": [],
            "is_open": False,
            "sources": []
        }

        # ===== 步骤1: 意图识别 =====
        yield "thinking_step", {"step": 1, "label": "意图识别", "status": "processing", "content": ""}
        try:
            prompt = intent_recognition_prompt(question)
            intent_response = self.llm.generate(prompt)
            intent = parse_intent_recognition(intent_response)
            result["intent"] = intent
        except:
            intent = "检索问题"
            result["intent"] = intent
        yield "thinking_step", {"step": 1, "label": "意图识别", "status": "done", "content": intent}

        if "开放" in intent:
            result["is_open"] = True
            try:
                prompt = open_question_prompt(question)
                yield "meta", result
                for chunk in self.llm.generate_stream(prompt):
                    result["answer"] += chunk
                    yield "chunk", chunk
            except Exception as e:
                result["answer"] = f"回答生成失败: {str(e)}"
                yield "chunk", result["answer"]
            yield "done", result
            return

        # ===== 步骤2: 实体提取 =====
        yield "thinking_step", {"step": 2, "label": "实体提取", "status": "processing", "content": ""}
        try:
            prompt = entity_recognition_prompt(question)
            entity_response = self.llm.generate(prompt)
            entities = parse_entity_recognition(entity_response)
            result["entities"] = entities
        except:
            entities = []
        yield "thinking_step", {"step": 2, "label": "实体提取", "status": "done", "content": entities}

        if not entities:
            result["answer"] = "无法识别您问题中的公司名称，请重新描述您的问题。"
            yield "meta", result
            yield "chunk", result["answer"]
            yield "done", result
            return

        company_name = entities[0]
        year = ""
        for e in entities[1:]:
            m = re.search(r"(\d{4})", e)
            if m:
                year = m.group(1)
                break

        # ===== 步骤3: 文件匹配 =====
        yield "thinking_step", {"step": 3, "label": "匹配文件", "status": "processing", "content": ""}
        txt_path = self._find_txt_file(entities)

        if not txt_path:
            result["sources"].append("知识库无数据")
            result["answer"] = f"知识库中没有「{company_name}」的财报数据。请检查公司名称或上传PDF年报。"
            yield "thinking_step", {"step": 3, "label": "匹配文件", "status": "error", "content": f"未找到 {company_name} 的财报文件"}
            yield "meta", result
            yield "chunk", result["answer"]
            yield "done", result
            return

        result["file"] = os.path.basename(txt_path)
        result["sources"].append("知识库")
        yield "thinking_step", {"step": 3, "label": "匹配文件", "status": "done", "content": os.path.basename(txt_path)}

        # 使用财务专用读取方法，获取更全面的财务数据
        file_content = self._read_txt_file_for_finance(txt_path, max_lines=8000)

        if not file_content:
            result["answer"] = "[财报数据已找到，但未检索到相关内容]"
            yield "meta", result
            yield "chunk", result["answer"]
            yield "done", result
            return

        # ===== 步骤4: 上下文检索 =====
        yield "thinking_step", {"step": 4, "label": "检索上下文", "status": "processing", "content": ""}
        import re as _re
        raw_lines = file_content.split("\n")
        
        def is_valid_data_line(line):
            line_stripped = line.strip()
            if not line_stripped or len(line_stripped) < 6:
                return False
            skip_patterns = [
                "词语释义", "含义如下", "下列词语", "非文义", "指，",
                "指'", "指\"", "公司全称", "公司全资子", "公司股东",
                "公司参股", "曾用名", "报告期", "中国证监会", "上交所",
                "深交所", "公司的中文名称", "公司的外文名称", "外文名称缩写",
                "法定代表人", "董事会秘书", "证券事务代表", "注册地址",
                "办公地址", "邮政编码", "公司网址", "电子信箱", "联系电话",
                "传真", "邮箱", "信息披露", "投资者关系", "联系人",
                "年度报告", "半年度报告", "季度报告", "定期报告",
                "第一节", "第二节", "第三节", "第四节", "第五节",
                "第六节", "第七节", "第八节", "第九节", "第十节",
                "第十一节", "第十二节", "第十三节", "第十四节",
                "释义", "定义", "声明", "承诺", "确认"
            ]
            for pat in skip_patterns:
                if pat in line_stripped:
                    return False
            has_number = bool(_re.search(r'[\d,]+\.?\d*%', line_stripped)) or \
                        bool(_re.search(r'[\d,]+\.\d+', line_stripped)) or \
                        bool(_re.search(r'[-]?\d[\d,]*\.\d+', line_stripped)) or \
                        bool(_re.search(r'\b\d{4}\b', line_stripped))
            if not has_number:
                return False
            if line_stripped.startswith("'") and line_stripped.count("'") == 2 and len(line_stripped) < 20:
                return False
            return True
        
        valid_lines = [line.strip() for line in raw_lines if is_valid_data_line(line)]
        
        topic_keywords = {
            "收入": ["营业收入", "营业总收入", "主营业务收入", "销售收入", "营收", "业务收入"],
            "成本": ["营业成本", "主营业务成本", "销售成本", "成本", "生产成本"],
            "利润": ["净利润", "利润总额", "营业利润", "归属于母公司", "净利", "毛利润", "利润"],
            "毛利率": ["毛利率", "毛利", "毛利润率"],
            "净利率": ["净利率", "净利润率", "净利"],
            "资产": ["资产总计", "总资产", "流动资产", "非流动资产", "固定资产", "无形资产", "资产合计",
                     "应收账款", "应收票据", "预付款项", "其他应收款", "长期应收款"],
            "负债": ["负债合计", "总负债", "流动负债", "非流动负债", "短期借款", "长期借款", "应付", "预收",
                     "应付账款", "应付票据", "合同负债", "租赁负债"],
            "权益": ["所有者权益", "股东权益", "净资产", "归属于母公司", "实收资本", "股本"],
            "现金流": ["现金流量", "经营活动", "投资活动", "筹资活动", "现金净额", "现金流",
                      "销售商品、提供劳务收到的现金", "购买商品、接受劳务支付的现金",
                      "支付给职工", "收回投资收到的现金", "取得投资收益收到的现金",
                      "购建固定资产", "偿还债务支付的现金", "分配股利"],
            "ROE": ["ROE", "净资产收益率", "股东回报", "权益报酬"],
            "比率": ["流动比率", "速动比率", "资产负债率", "偿债能力", "比率"],
            "增长": ["增长率", "同比增长", "环比增长", "增速", "增长", "增幅"],
            "费用": ["销售费用", "管理费用", "研发费用", "财务费用", "期间费用", "费用"],
            "员工": ["员工", "职工", "薪酬", "人数", "工资"],
            "分红": ["分红", "股息", "股利", "派息"],
            "存货": ["存货", "库存", "存货跌价", "存货减值"],
            "应收": ["应收账款", "应收票据", "坏账", "坏账准备", "应收账款周转"],
            "非经常性": ["非经常性损益", "非经常性", "营业外收入", "营业外支出", "政府补助",
                        "资产处置", "公允价值变动"],
            "减值": ["减值准备", "减值损失", "信用减值", "资产减值", "商誉减值", "存货跌价"],
            "商誉": ["商誉", "商誉减值"],
            "估值": ["市盈率", "PE", "每股收益", "EPS", "每股净资产", "BPS",
                   "市净率", "PB", "总市值", "市值", "总股本", "股本总额",
                   "流通股", "非流通股", "普通股股数", "股份总数",
                   "基本每股收益", "稀释每股收益", "加权平均", "每股"],
        }
        
        matched_topics = set()
        for topic, keywords in topic_keywords.items():
            for kw in keywords:
                if kw in question:
                    matched_topics.add(topic)
                    break
        
        # 默认匹配所有重要财务主题，确保数据完整
        if not matched_topics:
            matched_topics = {"收入", "成本", "利润", "资产", "负债", "现金流", "非经常性", "减值", "估值"}
        
        all_topic_keywords = set()
        for t in matched_topics:
            all_topic_keywords.update(topic_keywords.get(t, []))
        
        if matched_topics:
            filtered = []
            for line in valid_lines:
                if any(kw in line for kw in all_topic_keywords):
                    filtered.append(line)
            if len(filtered) >= 5:
                context_lines = filtered[:80]  # 增加到80行
            else:
                context_lines = valid_lines[:100]  # 增加到100行
        else:
            context_lines = valid_lines[:100]
        
        seen = set()
        for ctx_line in context_lines:
            if ctx_line not in seen:
                result["context"].append(ctx_line)
                seen.add(ctx_line)

        # 步骤4完成，推送上下文检索结果
        context_preview = result["context"][:5] if result["context"] else []
        yield "thinking_step", {"step": 4, "label": "检索上下文", "status": "done", "content": context_preview}

        # 所有思考步骤完成，推送完整meta信息
        yield "meta", result
        
        try:
            prompt = answer_generation_prompt(file_content, question)
            for chunk in self.llm.generate_stream(prompt):
                result["answer"] += chunk
                yield "chunk", chunk
        except Exception as e:
            result["answer"] = f"答案生成失败: {str(e)}"
            yield "chunk", result["answer"]
        
        yield "done", result
    
    def invest_analysis(self, question, verbose=False):
        result = {
            "answer": "",
            "entities": [],
            "file": "",
            "sources": []
        }
        
        try:
            prompt = entity_recognition_prompt(question)
            entity_response = self.llm.generate(prompt)
            entities = parse_entity_recognition(entity_response)
            result["entities"] = entities
        except:
            entities = []
        
        if not entities:
            result["answer"] = "无法识别公司名称"
            return result
        
        company_name = entities[0]
        year = ""
        for e in entities[1:]:
            m = re.search(r"(\d{4})", e)
            if m:
                year = m.group(1)
                break
        
        analysis = self.llm_financial_analysis(company_name, year=year, verbose=verbose)
        
        if analysis.get("error"):
            result["answer"] = f"财务分析失败: {analysis['error']}"
            return result
        
        calculations = analysis.get("calculations", {})
        calc_text = "\n".join([f"- {k}: {v}" for k, v in calculations.items()])
        raw_data = "\n".join(analysis.get("raw_context", []))
        
        try:
            query_text = f"公司：{company_name}\n年份：{year or '未指定'}\n\n财务指标数据：\n{calc_text}\n\n原始财报数据：\n{raw_data}"
            prompt = invest_analysis_raw_prompt().format(query=query_text)
            answer = self.llm.generate(prompt)
            result["answer"] = answer
            result["sources"].append("知识库+LLM分析")
        except Exception as e:
            result["answer"] = f"投资分析生成失败: {str(e)}"
        
        return result

    def invest_analysis_stream(self, question, verbose=False):
        result = {
            "answer": "",
            "entities": [],
            "file": "",
            "sources": []
        }

        # ===== 步骤1: 实体提取 =====
        yield "thinking_step", {"step": 1, "label": "实体提取", "status": "processing", "content": ""}
        try:
            prompt = entity_recognition_prompt(question)
            entity_response = self.llm.generate(prompt)
            entities = parse_entity_recognition(entity_response)
            result["entities"] = entities
        except:
            entities = []
        yield "thinking_step", {"step": 1, "label": "实体提取", "status": "done", "content": entities}

        if not entities:
            result["answer"] = "无法识别公司名称"
            yield "meta", result
            yield "chunk", result["answer"]
            yield "done", result
            return

        company_name = entities[0]
        year = ""
        for e in entities[1:]:
            m = re.search(r"(\d{4})", e)
            if m:
                year = m.group(1)
                break

        # 如果entities中没有年份，从问题文本中兜底提取
        if not year:
            m = re.search(r"(\d{4})", question)
            if m:
                year = m.group(1)
                entities.append(year + "年")
                result["entities"] = entities

        # ===== 步骤2: 财务指标计算 =====
        yield "thinking_step", {"step": 2, "label": "财务指标计算", "status": "processing", "content": ""}
        analysis = self.llm_financial_analysis(company_name, year=year, verbose=verbose)

        if analysis.get("error"):
            yield "thinking_step", {"step": 2, "label": "财务指标计算", "status": "error", "content": analysis["error"]}
            result["answer"] = f"财务分析失败: {analysis['error']}"
            yield "meta", result
            yield "chunk", result["answer"]
            yield "done", result
            return

        calculations = analysis.get("calculations", {})
        calc_keys = list(calculations.keys())[:5]
        yield "thinking_step", {"step": 2, "label": "财务指标计算", "status": "done", "content": f"已计算 {len(calculations)} 项指标"}

        # ===== 步骤3: 生成投资分析报告 =====
        calc_text = "\n".join([f"- {k}: {v}" for k, v in calculations.items()])
        raw_data = "\n".join(analysis.get("raw_context", []))
        yield "thinking_step", {"step": 3, "label": "生成投资分析", "status": "processing", "content": ""}

        result["sources"].append("知识库+LLM分析")
        yield "meta", result

        try:
            query_text = f"公司：{company_name}\n年份：{year or '未指定'}\n\n财务指标数据：\n{calc_text}\n\n原始财报数据：\n{raw_data}"
            prompt = invest_analysis_raw_prompt().format(query=query_text)
            for chunk in self.llm.generate_stream(prompt):
                result["answer"] += chunk
                yield "chunk", chunk
        except Exception as e:
            result["answer"] = f"投资分析生成失败: {str(e)}"
            yield "chunk", result["answer"]

        yield "thinking_step", {"step": 3, "label": "生成投资分析", "status": "done", "content": "分析完成"}
        yield "done", result
    
    def llm_financial_analysis(self, company_name, year="", verbose=False):
        result = {
            "calculations": {},
            "radar_data": {},
            "gross_margin_trend": [],
            "raw_context": [],
            "error": None
        }
        
        txt_path = self._find_txt_file([company_name, year] if year else [company_name])
        
        if not txt_path:
            has_any = False
            for key in self.txt_files:
                if company_name in key:
                    has_any = True
                    break
            if year and has_any:
                result["error"] = f"知识库中没有{company_name}{year}年的财报数据"
            elif not has_any:
                result["error"] = f"知识库中没有{company_name}的财报数据"
            else:
                result["error"] = f"未找到{company_name}的财报文件"
            return result
        
        file_content = self._read_txt_file_for_finance(txt_path, max_lines=10000)
        
        if not file_content:
            result["error"] = f"财报文件为空: {company_name}"
            return result
        
        result["raw_context"].append(file_content[:8000])
        
        try:
            prompt_template = financial_analysis_prompt(
                company=company_name,
                year=year or "未指定",
                context=file_content
            )
            prompt = prompt_template.format(
                company=company_name,
                year=year or "未指定",
                context=file_content
            )
            llm_response = self.llm.generate(prompt, max_tokens=4096)
            
            def extract_json(text):
                text = text.strip()
                start = 0
                while True:
                    idx = text.find('{', start)
                    if idx == -1:
                        return None
                    rest = text[idx+1:]
                    next_char = rest[0] if rest else ''
                    if next_char == '"' or next_char.isalpha() or next_char in ('\n', '\r', ' ', '\t'):
                        depth = 0
                        for i in range(idx, len(text)):
                            ch = text[i]
                            if ch == '{':
                                depth += 1
                            elif ch == '}':
                                depth -= 1
                                if depth == 0:
                                    candidate = text[idx:i+1]
                                    try:
                                        json.loads(candidate)
                                        return candidate
                                    except:
                                        break
                        return None
                    start = idx + 1
                return None
            
            def fix_json(s):
                s = s.strip()
                if not s:
                    return None
                for attempt in [s, s.replace("'", '"')]:
                    import re
                    cleaned = re.sub(r',\s*([}\]])', r'\1', attempt)
                    cleaned = re.sub(r'[\x00-\x1f\x7f]', '', cleaned)
                    try:
                        return json.loads(cleaned)
                    except:
                        pass
                try:
                    return json.loads(s, strict=False)
                except:
                    return None
            
            json_str = extract_json(llm_response)
            if not json_str:
                if verbose:
                    print(f"[LLM财务分析] LLM返回内容(前500字): {llm_response[:500]}", flush=True)
                result["error"] = "LLM返回格式异常，无法解析JSON"
                return result
            
            analysis_data = fix_json(json_str)
            if analysis_data is None:
                if verbose:
                    print(f"[LLM财务分析] JSON内容(前300字): {json_str[:300]}", flush=True)
                result["error"] = "LLM返回格式异常，无法解析JSON"
                return result
            calculations = {}
            
            for key in ["current_ratio", "quick_ratio", "cash_short_loan_ratio", 
                        "debt_ratio", "gross_margin", "net_margin", "roe",
                        "revenue_growth", "non_recurring_profit_ratio", "per_capita_salary"]:
                val = analysis_data.get(key)
                if val is not None and val != "无" and val != "无数据" and val != "无短期借款":
                    try:
                        calculations[key] = float(val)
                    except (ValueError, TypeError):
                        calculations[key] = val
                else:
                    calculations[key] = val
            
            result["calculations"] = calculations
            
            radar_scores = analysis_data.get("radar_scores", {})
            if isinstance(radar_scores, dict) and len(radar_scores) > 0:
                score_map = {
                    "流动比率": "流动比率", "速动比率": "速动比率",
                    "货币资金/短期借款": "货币资金/短期借款", "资产负债率": "资产负债率",
                    "非经常性损益占比": "非经常性损益占比", "人均薪酬": "人均薪酬",
                    "毛利率": "毛利率", "净利率": "净利率", "ROE": "ROE", "营收增长率": "营收增长率"
                }
                for cn_key, out_key in score_map.items():
                    val = radar_scores.get(cn_key)
                    if val is not None and val != "" and val != "无" and val != "无数据":
                        try:
                            score = float(val)
                            score = max(0.0, min(100.0, score))
                            result["radar_data"][out_key] = round(score, 1)
                        except (ValueError, TypeError):
                            pass
            else:
                def get_first_valid_value(d, *keys):
                    for k in keys:
                        v = d.get(k)
                        if v is not None and v != "" and v != "无数据" and v != "无" and v != "无短期借款":
                            try:
                                return float(v)
                            except:
                                pass
                    return None
                cr = get_first_valid_value(calculations, "current_ratio")
                if cr is not None:
                    result["radar_data"]["流动比率"] = round(min(max(cr / 2.0 * 100, 0), 100), 1)
                
                qr = get_first_valid_value(calculations, "quick_ratio")
                if qr is not None:
                    result["radar_data"]["速动比率"] = round(min(max(qr / 1.5 * 100, 0), 100), 1)
                
                csr = get_first_valid_value(calculations, "cash_short_loan_ratio")
                if csr is not None:
                    if csr >= 10:
                        result["radar_data"]["货币资金/短期借款"] = 100.0
                    else:
                        result["radar_data"]["货币资金/短期借款"] = round(min(max(csr / 5.0 * 100, 0), 100), 1)
                
                dr = get_first_valid_value(calculations, "debt_ratio")
                if dr is not None:
                    if dr <= 40:
                        result["radar_data"]["资产负债率"] = 95.0
                    elif dr <= 60:
                        result["radar_data"]["资产负债率"] = 85.0
                    elif dr <= 80:
                        result["radar_data"]["资产负债率"] = round(min(max((80 - dr) / 20 * 60 + 25, 25), 85), 1)
                    else:
                        result["radar_data"]["资产负债率"] = round(max(min((90 - dr) / 10 * 25, 0), 0), 1)
                
                gm = get_first_valid_value(calculations, "gross_margin")
                if gm is not None:
                    if gm >= 50:
                        result["radar_data"]["毛利率"] = 95.0
                    elif gm >= 25:
                        result["radar_data"]["毛利率"] = round(min(max(gm / 50 * 90 + 5, 50), 95), 1)
                    elif gm >= 10:
                        result["radar_data"]["毛利率"] = round(min(max((gm - 10) / 15 * 35 + 25, 25), 50), 1)
                    else:
                        result["radar_data"]["毛利率"] = round(min(max(gm / 10 * 25, 0), 25), 1)
                
                nm = get_first_valid_value(calculations, "net_margin")
                if nm is not None:
                    if nm >= 20:
                        result["radar_data"]["净利率"] = 95.0
                    elif nm >= 8:
                        result["radar_data"]["净利率"] = round(min(max(nm / 20 * 85 + 10, 50), 95), 1)
                    else:
                        result["radar_data"]["净利率"] = round(min(max(nm / 8 * 50, 0), 50), 1)
                
                roe = get_first_valid_value(calculations, "roe")
                if roe is not None:
                    if roe >= 20:
                        result["radar_data"]["ROE"] = 95.0
                    elif roe >= 8:
                        result["radar_data"]["ROE"] = round(min(max(roe / 20 * 80 + 15, 45), 95), 1)
                    else:
                        result["radar_data"]["ROE"] = round(min(max(roe / 8 * 45, 0), 45), 1)
                
                rg = get_first_valid_value(calculations, "revenue_growth")
                if rg is not None:
                    if rg >= 20:
                        result["radar_data"]["营收增长率"] = 95.0
                    elif rg >= 8:
                        result["radar_data"]["营收增长率"] = round(min(max(rg / 20 * 80 + 15, 50), 95), 1)
                    elif rg >= 0:
                        result["radar_data"]["营收增长率"] = round(min(max(rg / 8 * 50, 25), 50), 1)
                    elif rg >= -10:
                        result["radar_data"]["营收增长率"] = round(min(max((10 + rg) / 10 * 25, 0), 25), 1)
                    else:
                        result["radar_data"]["营收增长率"] = round(max(min((rg + 30) / 20 * 10, 0), 0), 1)
                
                nrp = get_first_valid_value(calculations, "non_recurring_profit_ratio")
                if nrp is not None:
                    if nrp <= 5:
                        result["radar_data"]["非经常性损益占比"] = 95.0
                    elif nrp <= 20:
                        result["radar_data"]["非经常性损益占比"] = round(min(max((20 - nrp) / 15 * 30 + 65, 65), 95), 1)
                    else:
                        result["radar_data"]["非经常性损益占比"] = round(max(min((50 - nrp) / 30 * 50, 10), 10), 1)
                
                per_capita = calculations.get("per_capita_salary")
                if per_capita and per_capita not in ("无数据", "无", "无短期借款", None):
                    try:
                        pc_val = float(per_capita)
                        if pc_val >= 300000:
                            result["radar_data"]["人均薪酬"] = 95.0
                        elif pc_val >= 150000:
                            result["radar_data"]["人均薪酬"] = round(min(max((pc_val - 150000) / 150000 * 25 + 70, 70), 95), 1)
                        elif pc_val >= 50000:
                            result["radar_data"]["人均薪酬"] = round(min(max((pc_val - 50000) / 100000 * 40 + 30, 30), 70), 1)
                        else:
                            result["radar_data"]["人均薪酬"] = round(min(max(pc_val / 50000 * 30, 0), 30), 1)
                    except:
                        pass
            
            trend_data = self._build_net_profit_trend(company_name, year)
            if trend_data and len(trend_data) >= 2:
                result["gross_margin_trend"] = trend_data
            else:
                llm_trend = analysis_data.get("net_profit_trend", []) or analysis_data.get("gross_margin_trend", [])
                if llm_trend and isinstance(llm_trend, list) and len(llm_trend) >= 2:
                    result["gross_margin_trend"] = [round(v, 2) for v in llm_trend if isinstance(v, (int, float))]
                elif trend_data:
                    result["gross_margin_trend"] = trend_data
                elif llm_trend:
                    result["gross_margin_trend"] = [round(v, 2) for v in llm_trend if isinstance(v, (int, float))]
            
            if calculations.get("per_capita_salary") in ("无数据", "无", None):
                salary = self._extract_per_capita_salary(file_content)
                if salary is not None:
                    calculations["per_capita_salary"] = salary
                    result["calculations"] = calculations
                    if "人均薪酬" not in result["radar_data"]:
                        pc_val = float(salary)
                        if pc_val >= 300000:
                            result["radar_data"]["人均薪酬"] = 95.0
                        elif pc_val >= 150000:
                            result["radar_data"]["人均薪酬"] = round(min(max((pc_val - 150000) / 150000 * 25 + 70, 70), 95), 1)
                        elif pc_val >= 50000:
                            result["radar_data"]["人均薪酬"] = round(min(max((pc_val - 50000) / 100000 * 40 + 30, 30), 70), 1)
                        else:
                            result["radar_data"]["人均薪酬"] = round(min(max(pc_val / 50000 * 30, 0), 30), 1)
            
            if verbose:
                print(f"[LLM财务分析] 成功! calculations: {list(calculations.keys())}", flush=True)
                print(f"[LLM财务分析] radar_data: {list(result['radar_data'].keys())}", flush=True)
                
        except Exception as e:
            result["error"] = f"解析LLM结果失败: {str(e)}"
            if verbose:
                import traceback
                traceback.print_exc()
        
        return result
    
    def career_analysis(self, companies_data, verbose=False):
        result = {
            "answer": ""
        }
        
        data_text = ""
        for cd in companies_data:
            company = cd.get("company", "")
            calculations = cd.get("calculations", {})
            radar_data = cd.get("radar_data", {})
            
            data_text += f"\n### {company}\n"
            data_text += "财务指标:\n"
            for k, v in calculations.items():
                data_text += f"- {k}: {v}\n"
            data_text += "雷达图数据:\n"
            for k, v in radar_data.items():
                data_text += f"- {k}: {v}\n"
        
        try:
            prompt = career_analysis_raw_prompt().format(
                query=data_text
            )
            answer = self.llm.generate(prompt, max_tokens=4096)
            result["answer"] = answer
        except Exception as e:
            result["answer"] = f"职业分析生成失败: {str(e)}"
        
        return result
    
    def _build_fallback_answer(self, company_name: str, web_data: dict, question: str = "") -> str:
        results = web_data.get("results", [])
        
        if not results:
            return (
                f"通过互联网搜索了「{company_name}」的相关信息，"
                f"但未找到足够有用的财务数据。\n\n"
                f"可能原因：\n"
                f"1. 该公司可能未上市或未公开财务数据\n"
                f"2. 搜索结果与财务问题关联度不高\n\n"
                f"建议：请上传该公司的PDF财报文件以获取精确的财务分析。"
            )
        
        parts = []
        parts.append(f"**{company_name}** - 联网搜索结果\n")
        parts.append(f"以下信息来自互联网搜索（非官方财报数据），仅供参考：\n")
        
        for i, r in enumerate(results[:6], 1):
            title = r.get('title', '')
            snippet = r.get('snippet', '')
            source = r.get('source', '')
            
            if title:
                parts.append(f"**{i}. {title}**")
                if source:
                    parts.append(f"   来源: {source}")
                if snippet:
                    clean_snippet = snippet[:200] + "..." if len(snippet) > 200 else snippet
                    parts.append(f"   {clean_snippet}")
                parts.append("")
        
        parts.append(
            "---\n\n"
            "以上为搜索摘要。如需详细准确的财务分析，"
            f"建议上传「{company_name}」的PDF年报文件。"
        )
        
        return "\n".join(parts)


def main():
    bot = ChatFinance()

    print("\n" + "=" * 55)
    print("  ChatFinance - 金融财报智能问答系统")
    print("=" * 55)

    print("\n选择运行模式:")

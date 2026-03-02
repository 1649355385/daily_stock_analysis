# src/analyzer.py 完整修复代码
import os
import logging
import litellm
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    """AI 分析器（适配 AIHubMix + litellm）"""
    
    def __init__(self, api_key: Optional[str] = None):
        # 优先从环境变量读取 AIHubMix Key（GitHub Secrets 注入）
        self.aihubmix_key = api_key or os.getenv("AIHUBMIX_KEY")
        
        # 配置 litellm 适配 AIHubMix（核心修复）
        if self.aihubmix_key:
            litellm.api_key = self.aihubmix_key
            # AIHubMix 专属 base_url，必须配置
            litellm.base_url = "https://api.aihubmix.com/v1"
            logger.info("✅ AIHubMix 配置已生效")
        else:
            logger.error("❌ 未配置 AIHUBMIX_KEY！请检查 GitHub Secrets")
        
        # 默认使用 AIHubMix 免费模型
        self.default_model = "gpt-4o-free"

    def is_available(self) -> bool:
        """检查 AI 分析器是否可用"""
        return bool(self.aihubmix_key)

    def analyze_stock(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析单只股票数据，返回 AI 分析结果
        :param stock_data: 股票基础数据（包含代码、名称、行情等）
        :return: 分析结果（操作建议、评分、走势、一句话决策等）
        """
        if not self.is_available():
            logger.error("AI 分析器不可用，返回默认结果")
            return self._get_default_result(stock_data)
        
        try:
            # 1. 构建股票分析提示词（贴合你的交易理念）
            prompt = self._build_stock_prompt(stock_data)
            
            # 2. 调用 litellm + AIHubMix 生成分析
            response = litellm.completion(
                model=self.default_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=800,
                timeout=30  # 延长超时时间，避免连接超时
            )
            
            # 3. 解析 AI 回复
            ai_content = response.choices[0].message.content.strip()
            return self._parse_ai_response(ai_content, stock_data)
            
        except Exception as e:
            logger.error(f"分析 {stock_data.get('code')} 失败: {str(e)}", exc_info=True)
            return self._get_default_result(stock_data)

    def _build_stock_prompt(self, stock_data: Dict[str, Any]) -> str:
        """构建股票分析提示词"""
        stock_code = stock_data.get("code", "")
        stock_name = stock_data.get("name", "")
        price = stock_data.get("price", 0)
        ma5 = stock_data.get("ma5", 0)
        ma10 = stock_data.get("ma10", 0)
        ma20 = stock_data.get("ma20", 0)
        deviation = stock_data.get("deviation", 0)  # 乖离率
        
        # 融合你的交易理念到提示词中
        prompt = f"""
请严格按照以下规则分析股票 {stock_name}({stock_code})：
交易规则：
1. 严进策略：乖离率 > 5% 不买入
2. 趋势交易：只做 MA5>MA10>MA20 多头排列
3. 效率优先：关注筹码集中度好的股票
4. 买点偏好：缩量回踩 MA5/MA10 支撑

基础数据：
- 当前价格：{price}
- MA5：{ma5} | MA10：{ma10} | MA20：{ma20}
- 乖离率：{deviation}%

输出要求（严格按格式返回，不要多余内容）：
1. 操作建议：仅返回 买入/持有/卖出 其中一个
2. 评分：0-100 分（整数）
3. 走势判断：仅返回 上涨/震荡/下跌 其中一个
4. 一句话决策：简洁明了，不超过 50 字
5. 风险提示：1-2 句话，贴合当前行情
"""
        return prompt.strip()

    def _parse_ai_response(self, ai_content: str, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析 AI 回复，提取关键信息"""
        # 简化解析逻辑（新手友好版）
        result = {
            "code": stock_data.get("code", ""),
            "name": stock_data.get("name", ""),
            "operation_advice": "持有",
            "sentiment_score": 50,
            "trend_prediction": "震荡",
            "one_sentence_decision": "当前市场数据波动，建议短期持有观察走势",
            "risk_tips": "AI 分析完成，可结合基本面手动判断"
        }
        
        # 按关键词提取 AI 回复内容
        lines = ai_content.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 提取操作建议
            if line.startswith("操作建议："):
                result["operation_advice"] = line.replace("操作建议：", "").strip()
            # 提取评分
            elif line.startswith("评分："):
                try:
                    result["sentiment_score"] = int(line.replace("评分：", "").strip())
                except:
                    pass
            # 提取走势判断
            elif line.startswith("走势判断："):
                result["trend_prediction"] = line.replace("走势判断：", "").strip()
            # 提取一句话决策
            elif line.startswith("一句话决策："):
                result["one_sentence_decision"] = line.replace("一句话决策：", "").strip()
            # 提取风险提示
            elif line.startswith("风险提示："):
                result["risk_tips"] = line.replace("风险提示：", "").strip()
        
        return result

    def _get_default_result(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """返回默认结果（AI 调用失败时兜底）"""
        return {
            "code": stock_data.get("code", ""),
            "name": stock_data.get("name", ""),
            "operation_advice": "持有",
            "sentiment_score": 50,
            "trend_prediction": "震荡",
            "one_sentence_decision": "AI 配置未完成，建议手动分析",
            "risk_tips": "请检查 AIHubMix Key 配置，或稍后重试"
        }

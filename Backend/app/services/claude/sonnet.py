# app/services/claude/sonnet.py
"""
Sonnet 모델
인사이트 추출
전략 보고서 생성
결과 검증
"""
from anthropic import Anthropic
from typing import Dict, Any, List, Optional
import re
import json

from app.config.settings import get_settings
from app.services.prompts import PromptTemplates
from .base import ClaudeBase

settings = get_settings()


class SonnetService(ClaudeBase):
    def __init__(self):
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.prompt_templates = PromptTemplates()
    
    def extract_insights(
        self, 
        panel_data: List[Dict[str, Any]], 
        original_query: str = None,
        full_statistics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        통합 인사이트 추출:
        1) 의미 기반 토픽 추출 (새로 추가)
        2) 상세 패턴 발견 (기존 유지)
        3) 자연스러운 요약 생성 (새로 추가)
        """
        try:
            # ===== 1) 의미 기반 토픽 추출 (새로 추가) =====
            semantic_topics = self._extract_semantic_topics(panel_data)
            
            # ===== 2) 상세 패턴 발견 (기존 로직) =====
            sample_size = min(50, len(panel_data))
            sampled_data = panel_data[:sample_size]
            
            prompt = self.prompt_templates.insight_extraction_prompt(
                sampled_data, 
                original_query or "사용자 질의 없음",
                full_statistics
            )
            
            system_message = self.prompt_templates.get_system_message('insight_extractor')
            
            message = self.client.messages.create(
                model=settings.CLAUDE_INSIGHT_EXTRACTION_MODEL, 
                max_tokens=settings.max_tokens,
                system=system_message,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text.strip()
            parsed_result = self.parse_json_response(response_text)
            
            if not parsed_result:
                return {
                    "success": False,
                    "data": None,
                    "error": "JSON 파싱 실패"
                }
            
            # 필터링 (기존 로직)
            filtered_patterns = self._filter_invalid_insights(
                parsed_result.get('hidden_patterns', [])
            )
            
            # ===== 3) 자연스러운 요약 생성 (새로 추가) =====
            insight_summary = self._generate_natural_summary(
                semantic_topics,
                filtered_patterns,
                full_statistics,
                original_query
            )
            
            # ===== 최종 결과 통합 =====
            return {
                "success": True,
                "data": {
                    "summary": insight_summary,
                    "semantic_topics": semantic_topics,
                    "hidden_patterns": filtered_patterns
                },
                "raw_response": response_text,
                "filtered_count": {
                    "valid": len(filtered_patterns),
                    "removed": len(parsed_result.get('hidden_patterns', [])) - len(filtered_patterns)
                }
            }
            
        except Exception as e:
            print(f"Insight Extraction Error: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    def _extract_semantic_topics(self, panel_data: List[Dict]) -> List[str]:
        """
        answer_text에서 의미 기반 토픽 추출
        """
        qa_texts = []
        for panel in panel_data[:50]:
            text = panel.get('answer_text', '')
            if text:
                qa_pattern = r"'([^']+)'\s*질문에\s*'([^']+)'라고\s*답했습니다"
                matches = re.findall(qa_pattern, text)
                qa_texts.extend([f"{q}: {a}" for q, a in matches])
        
        if not qa_texts:
            return []
        
        qa_sample = list(set(qa_texts))[:100]
        
        prompt = f"""
다음 설문 응답들에서 공통적으로 나타나는 관심사/특성을 정확히 2개만 추출하세요.

{chr(10).join(qa_sample)}

출력: ["토픽1", "토픽2"]
"""
        
        try:
            from app.services.claude.haiku import HaikuService
            haiku = HaikuService()
            
            response = haiku.client.messages.create(
                model=settings.CLAUDE_SQL_GENERATION_MODEL,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            topics = json.loads(response.content[0].text.strip())
            return topics[:2] if isinstance(topics, list) else []
            
        except Exception as e:
            print(f"토픽 추출 실패: {e}")
            return []
    
    def _select_supporting_stats(
        self,
        full_stats: Dict[str, Any],
        semantic_topics: List[str]
    ) -> Dict[str, Any]:
        """
        의미 토픽과 연관된 정형 통계만 선택
        """
        # 토픽별 연관 통계 매핑
        TOPIC_STAT_MAP = {
            'AI': ['job_distribution', 'education_distribution', 'age_distribution'],
            '기술': ['job_distribution', 'education_distribution'],
            '헬스': ['age_distribution', 'gender_distribution'],
            '건강': ['age_distribution', 'gender_distribution'],
            '운동': ['age_distribution', 'gender_distribution'],
            '소비': ['income_distribution', 'location_distribution'],
            '쇼핑': ['income_distribution', 'location_distribution'],
            '구매': ['income_distribution', 'location_distribution'],
            '여행': ['age_distribution', 'income_distribution'],
            '문화': ['age_distribution', 'education_distribution'],
            '엔터테인먼트': ['age_distribution', 'income_distribution'],
            '음악': ['age_distribution'],
            '영화': ['age_distribution'],
        }
        
        if not full_stats:
            return {}
        
        selected_stats = {}
        
        # 토픽 키워드 기반으로 관련 통계 선택
        for topic in semantic_topics:
            for keyword, stat_keys in TOPIC_STAT_MAP.items():
                if keyword in topic:
                    for stat_key in stat_keys:
                        if stat_key in full_stats:
                            selected_stats[stat_key] = full_stats[stat_key]
        
        # 최소한 기본 통계는 포함 (토픽 매칭 실패 시)
        if not selected_stats and full_stats:
            selected_stats['job_distribution'] = full_stats.get('job_distribution', {})
            selected_stats['age_distribution'] = full_stats.get('age_distribution', {})
        
        print(f"📊 전체 통계: {list(full_stats.keys())}")
        print(f"✅ 선택된 통계: {list(selected_stats.keys())}")
        
        return selected_stats
    
    def _generate_natural_summary(
        self,
        semantic_topics: List[str],
        patterns: List[Dict],
        full_stats: Dict,
        query: str
    ) -> str:
        """
        의미 토픽 + 상세 패턴 → 자연스러운 한 문단 생성
        """
        if not semantic_topics and not patterns:
            return "공통 특성을 발견하지 못했습니다."
        
        # 🆕 토픽 관련 통계만 선택
        supporting_stats = self._select_supporting_stats(full_stats, semantic_topics)
        
        # 상위 3개 패턴만 사용
        top_patterns = patterns[:3]
        
        pattern_summary = []
        for p in top_patterns:
            feature = p.get('feature', '')
            value = p.get('value', '')
            pct = p.get('percentage', 0)
            pattern_summary.append(f"{feature}: {value} ({pct}%)")
        
        # 통계를 읽기 쉬운 형태로 변환
        stats_text = []
        for key, value in supporting_stats.items():
            if isinstance(value, dict):
                top_items = sorted(value.items(), key=lambda x: x[1], reverse=True)[:3]
                stats_text.append(f"{key}: {top_items}")
        
        prompt = f"""
당신은 마케팅 리서치 전문가입니다.

검색 질의: "{query}"

다음 정보를 바탕으로 2-3문장의 자연스러운 한 문단으로 요약하세요.

의미적 특성:
{semantic_topics if semantic_topics else "없음"}

주요 패턴:
{chr(10).join(pattern_summary)}

관련 통계 (근거로 사용):
{chr(10).join(stats_text) if stats_text else "없음"}

규칙:
- 의미적 특성을 문단의 중심으로
- 주요 패턴과 통계는 자연스럽게 근거로 제시
- 불릿/헤더 금지, 한 문단만
- 통계 수치는 괄호 안에

예시:
"이 그룹은 AI·기술에 대한 관심이 뚜렷하며, IT 직군 비중(62%)과 대졸 이상 학력(80%)이 높아 디지털 친화적 특성을 보입니다."
"""
        
        try:
            response = self.client.messages.create(
                model=settings.CLAUDE_INSIGHT_EXTRACTION_MODEL,
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            print(f"요약 생성 실패: {e}")
            # Fallback: 패턴 기반 간단 요약
            if patterns:
                return f"이 그룹은 {patterns[0]['insight']}"
            return "인사이트를 생성할 수 없습니다."
    
    def generate_strategy_report(
        self,
        insights: Dict[str, Any],
        original_query: str,
        panel_count: int
    ) -> Dict[str, Any]:
        try:
            prompt = self.prompt_templates.strategy_report_prompt(
                insights,
                original_query,
                panel_count
            )
            
            system_message = self.prompt_templates.get_system_message('strategy_planner')
            
            message = self.client.messages.create(
                model=settings.CLAUDE_INSIGHT_EXTRACTION_MODEL,
                max_tokens=settings.max_tokens,
                system=system_message,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text.strip()
            print(f"\nRaw Strategy Report Response:\n{response_text}\n")
            
            parsed_result = self.parse_json_response(response_text)
            
            if parsed_result:
                return {
                    "success": True,
                    "data": parsed_result,
                    "raw_response": response_text
                }
            else:
                return {
                    "success": False,
                    "data": None,
                    "raw_response": response_text,
                    "error": "JSON 파싱 실패"
                }
                
        except Exception as e:
            print(f"Strategy Report Generation Error: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    def validate_results(
        self,
        sql_result: List[Dict],
        original_conditions: Dict,
        target_count: int
    ) -> Dict[str, Any]:
        try:
            prompt = self.prompt_templates.result_validation_prompt(
                sql_result,
                original_conditions,
                target_count
            )
            system_message = self.prompt_templates.get_system_message('validator')
            
            message = self.client.messages.create(
                model=settings.CLAUDE_RESULT_VALIDATION_MODEL,
                max_tokens=settings.max_tokens,
                system=system_message,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text.strip()
            parsed_result = self.parse_json_response(response_text)
            
            if parsed_result:
                return {
                    "success": True,
                    "data": parsed_result,
                    "raw_response": response_text
                }
            else:
                return {
                    "success": False,
                    "data": None,
                    "raw_response": response_text,
                    "error": "JSON 파싱 실패"
                }
                
        except Exception as e:
            print(f"Validation Error: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    @staticmethod
    def _filter_invalid_insights(patterns: List[Dict]) -> List[Dict]:
        filtered = []
        removed = []
        
        for pattern in patterns:
            feature = pattern.get('feature', '').lower()
            value = pattern.get('value', '').lower()
            insight = pattern.get('insight', '')
            
            is_unrecorded_topic = any(kw in feature for kw in [
                '미기재', '정보 없', '데이터 부족', '수집되지 않',
                '비공개', '기입하지 않', '입력하지 않',
                '알 수 없', '확인 불가', '누락', '부재'
            ])
            
            is_fully_unrecorded = any(phrase in value or phrase in insight for phrase in [
                '100% 미기재', '전원 미기재', '모두 미기재',
                '전체 미기재', '100%가 미기재'
            ])
            
            if is_unrecorded_topic or is_fully_unrecorded:
                removed.append(pattern)
                print(f"미기재 인사이트 제거: {feature} - {insight[:50]}...")
                continue
            
            filtered.append(pattern)
        
        print(f"유효한 인사이트: {len(filtered)}개")
        if removed:
            print(f"제거된 인사이트: {len(removed)}개")
        
        return filtered
# Install required packages
#!pip -q install -U tavily-python google-genai requests beautifulsoup4 python-dateutil

import textwrap
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from tavily import TavilyClient
from google import genai
from google.genai import types
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

# API Configuration
GEMINI_API_KEY = "AIzaSyC3wzdmA5aUPpMpaGYUXAX3s_EJyl-jSX8"
TAVILY_API_KEY = "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"

# Initialize clients with error handling
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
    tavily = TavilyClient(api_key=TAVILY_API_KEY)
    print("✅ API clients initialized successfully")
except Exception as e:
    print(f"❌ API initialization failed: {e}")
    print("Please check your API keys")
    exit()

# Advanced system prompt for deeper analysis
ADVANCED_SYSTEM = """You are an elite AI research assistant with expertise in comprehensive analysis and synthesis. 

CORE PRINCIPLES:
- Provide exhaustive, multi-layered analysis with unprecedented depth
- Cross-reference multiple sources for maximum accuracy
- Include historical context, current developments, and future implications
- Present nuanced perspectives and expert opinions
- Use structured, academic-level reasoning
- Prioritize recent, authoritative sources
- Synthesize information into coherent, insightful narratives

RESPONSE STRUCTURE:
1. Executive Summary (key findings)
2. Detailed Analysis (comprehensive exploration)
3. Multiple Perspectives (various viewpoints)
4. Historical Context (background and evolution)
5. Current Status (latest developments)
6. Expert Insights (authoritative opinions)
7. Future Implications (projections and trends)
8. Critical Assessment (strengths/limitations of available data)

QUALITY STANDARDS:
- Minimum 500-1000 words for complex topics
- Include specific dates, numbers, and verifiable facts
- Cross-validate information across sources
- Highlight any contradictions or uncertainties
- Provide actionable insights where applicable"""

class AdvancedSearchEngine:
    def __init__(self, tavily_client, max_searches=5):
        self.tavily = tavily_client
        self.max_searches = max_searches
        
    def multi_angle_search(self, query: str, topic_type: str = "general") -> Dict[str, Any]:
        """Perform multiple searches from different angles for comprehensive coverage"""
        
        search_strategies = self._generate_search_strategies(query, topic_type)
        all_results = []
        all_sources = set()
        combined_answer = ""
        
        print(f"🔍 Executing {len(search_strategies)} search strategies...")
        
        for i, (strategy_name, search_query, params) in enumerate(search_strategies[:self.max_searches], 1):
            print(f"   Strategy {i}: {strategy_name}")
            try:
                results, sources, direct = self._execute_search(search_query, params)
                if results:
                    all_results.extend(results)
                    all_sources.update(sources)
                    if direct and len(direct) > len(combined_answer):
                        combined_answer = direct
            except Exception as e:
                print(f"   ⚠️  Strategy {i} failed: {str(e)}")
                continue
                
        return {
            "results": all_results,
            "sources": list(all_sources),
            "combined_answer": combined_answer,
            "search_strategies_used": len(search_strategies)
        }
    
    def _generate_search_strategies(self, query: str, topic_type: str) -> List[Tuple[str, str, Dict]]:
        """Generate multiple search strategies for comprehensive coverage"""
        
        strategies = []
        base_params = {
            "search_depth": "advanced",
            "max_results": 8,
            "include_answer": True,
            "include_raw_content": True,
            "include_images": False,
        }
        
        # Strategy 1: Recent comprehensive search
        strategies.append((
            "Recent Comprehensive",
            query,
            {**base_params, "topic": topic_type}
        ))
        
        # Strategy 2: Academic/Research focused
        strategies.append((
            "Academic Research",
            f"{query} research study analysis report",
            {**base_params, "topic": "general"}
        ))
        
        # Strategy 3: News and current events
        if any(keyword in query.lower() for keyword in ['current', 'latest', 'recent', 'news', 'today']):
            strategies.append((
                "Breaking News",
                f"{query} latest news updates",
                {**base_params, "topic": "news"}
            ))
        
        # Strategy 4: Historical context
        strategies.append((
            "Historical Context",
            f"{query} history background context",
            {**base_params, "topic": "general"}
        ))
        
        # Strategy 5: Expert opinions and analysis
        strategies.append((
            "Expert Analysis",
            f"{query} expert opinion analysis perspective",
            {**base_params, "topic": "general", "max_results": 6}
        ))
        
        return strategies
    
    def _execute_search(self, query: str, params: Dict) -> Tuple[List[Dict], List[str], str]:
        """Execute a single search with given parameters"""
        
        resp = self.tavily.search(query=query, **params)
        results = resp.get("results", []) or []
        direct = resp.get("answer", "") or ""
        
        processed_results = []
        sources = []
        
        for i, r in enumerate(results, 1):
            title = r.get("title", "Untitled")
            url = r.get("url", "")
            content = r.get("content", "")
            published = r.get("published_date", "N/A")
            score = r.get("score", 0)
            
            # Enhanced content processing
            enhanced_content = self._enhance_content(content, url)
            
            processed_result = {
                "rank": i,
                "title": title,
                "url": url,
                "content": enhanced_content,
                "published_date": published,
                "relevance_score": score,
                "word_count": len(enhanced_content.split()),
                "recency_score": self._calculate_recency_score(published)
            }
            
            processed_results.append(processed_result)
            if url:
                sources.append(url)
        
        return processed_results, sources, direct
    
    def _enhance_content(self, content: str, url: str) -> str:
        """Enhance content with additional context and cleaning"""
        if not content:
            return ""
            
        # Clean and expand content
        content = re.sub(r'\s+', ' ', content).strip()
        content = content[:2000]  # Reasonable limit while keeping comprehensive
        
        return content
    
    def _calculate_recency_score(self, published_date: str) -> float:
        """Calculate recency score for prioritizing recent information"""
        if not published_date or published_date == "N/A":
            return 0.5
            
        try:
            pub_date = date_parser.parse(published_date)
            days_ago = (datetime.now() - pub_date).days
            
            # Score decreases with age: 1.0 for today, 0.9 for 1 day ago, etc.
            return max(0.1, 1.0 - (days_ago * 0.01))
        except:
            return 0.5

def format_comprehensive_results(search_data: Dict[str, Any]) -> str:
    """Format search results for comprehensive analysis"""
    
    results = search_data["results"]
    if not results:
        return "No comprehensive data available."
    
    # Sort results by relevance and recency
    sorted_results = sorted(
        results, 
        key=lambda x: (x.get("relevance_score", 0) * 0.7 + x.get("recency_score", 0) * 0.3),
        reverse=True
    )
    
    formatted_sections = []
    
    # Executive Summary from direct answer
    if search_data.get("combined_answer"):
        formatted_sections.append(f"🎯 **EXECUTIVE SUMMARY**\n{search_data['combined_answer']}\n")
    
    # Detailed findings
    formatted_sections.append("📊 **COMPREHENSIVE RESEARCH FINDINGS**")
    
    for i, result in enumerate(sorted_results[:10], 1):  # Top 10 most relevant
        title = result.get("title", "Untitled")
        content = result.get("content", "")
        url = result.get("url", "")
        published = result.get("published_date", "N/A")
        relevance = result.get("relevance_score", 0)
        recency = result.get("recency_score", 0)
        
        snippet = textwrap.shorten(content, width=800, placeholder="...")
        
        formatted_sections.append(
            f"\n**[{i}] {title}**\n"
            f"📅 Published: {published} | 🎯 Relevance: {relevance:.2f} | 🕒 Recency: {recency:.2f}\n"
            f"{snippet}\n"
            f"🔗 Source: {url}"
        )
    
    return "\n".join(formatted_sections)

# Enhanced function declarations for Gemini
tavily_comprehensive_decl = types.FunctionDeclaration(
    name="comprehensive_research",
    description="Perform comprehensive, multi-angle research with advanced analysis and deep insights. Use this for any query requiring thorough, accurate, and up-to-date information.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "query": types.Schema(
                type=types.Type.STRING,
                description="The research query to investigate comprehensively"
            ),
            "topic_type": types.Schema(
                type=types.Type.STRING,
                description="Type of topic: 'news', 'general', 'academic', 'business', 'technology', 'health', 'politics'",
                enum=["news", "general", "academic", "business", "technology", "health", "politics"]
            )
        },
        required=["query"],
    ),
)

# Corrected configuration - integrate generation config into the main config
config = types.GenerateContentConfig(
    tools=[types.Tool(function_declarations=[tavily_comprehensive_decl])],
    generation_config=types.GenerationConfig(
        max_output_tokens=8192,
        temperature=0.1,
        top_p=0.8,
        top_k=40
    )
)

# Initialize advanced search engine
search_engine = AdvancedSearchEngine(tavily, max_searches=5)

print("🚀 **ADVANCED GEMINI 2.5 + TAVILY RESEARCH SYSTEM**")
print("💡 Features: Multi-angle search, comprehensive analysis, unlimited depth")
print("📝 Type 'exit' to quit, 'help' for commands\n")

def run_research_session():
    while True:
        q = input("🔬 Research Query: ").strip()
        
        if q.lower() in ["exit", "quit"]:
            print("👋 Research session ended. Goodbye!")
            break
        elif q.lower() == "help":
            print("""
🔧 **AVAILABLE COMMANDS:**
- Any research query: Get comprehensive analysis
- 'exit' or 'quit': End session
- 'help': Show this help message

💡 **TIPS FOR BEST RESULTS:**
- Be specific about what you want to know
- Ask complex, multi-faceted questions
- Request analysis, comparisons, or deep insights
- System automatically determines optimal search strategies
            """)
            continue
        elif not q:
            continue

        print(f"\n🔍 **INITIATING COMPREHENSIVE RESEARCH**\n{'='*50}")
        
        try:
            # Determine topic type automatically
            topic_type = "general"
            if any(keyword in q.lower() for keyword in ['news', 'breaking', 'latest', 'current']):
                topic_type = "news"
            elif any(keyword in q.lower() for keyword in ['business', 'market', 'economy', 'finance']):
                topic_type = "business"
            elif any(keyword in q.lower() for keyword in ['technology', 'tech', 'ai', 'software']):
                topic_type = "technology"
            elif any(keyword in q.lower() for keyword in ['health', 'medical', 'medicine', 'disease']):
                topic_type = "health"
            elif any(keyword in q.lower() for keyword in ['politics', 'government', 'policy', 'election']):
                topic_type = "politics"
            
            # Create enhanced content for Gemini
            contents = [
                types.Content(role="user", parts=[types.Part(text=ADVANCED_SYSTEM)]),
                types.Content(role="user", parts=[types.Part(text=f"Conduct comprehensive research and provide deep analysis on: {q}")]),
            ]
            
            # Initial model call with corrected config
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=config
            )
            
            function_call_found = False
            
            # Check for function calls
            if resp.candidates and resp.candidates[0].content and resp.candidates[0].content.parts:
                for part in resp.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        function_call_found = True
                        fc = part.function_call
                        
                        # Extract parameters
                        query_for_research = fc.args.get("query", q)
                        detected_topic = fc.args.get("topic_type", topic_type)
                        
                        print(f"🎯 Research Focus: {detected_topic.upper()}")
                        
                        # Perform comprehensive research
                        search_data = search_engine.multi_angle_search(query_for_research, detected_topic)
                        comprehensive_results = format_comprehensive_results(search_data)
                        
                        print(f"✅ Research Complete: {len(search_data['results'])} sources analyzed")
                        print(f"🔍 Search strategies used: {search_data['search_strategies_used']}\n")
                        
                        # Create function response
                        function_response_part = types.Part(
                            function_response=types.FunctionResponse(
                                name=fc.name,
                                response={
                                    "research_data": comprehensive_results,
                                    "total_sources": len(search_data['sources']),
                                    "analysis_depth": "comprehensive",
                                    "search_strategies": search_data['search_strategies_used']
                                }
                            )
                        )
                        
                        # Final comprehensive analysis
                        final_resp = client.models.generate_content(
                            model="gemini-2.5-flash",
                            config=config,
                            contents=[
                                types.Content(role="user", parts=[types.Part(text=ADVANCED_SYSTEM)]),
                                types.Content(role="user", parts=[types.Part(text=f"Provide comprehensive analysis on: {q}")]),
                                resp.candidates[0].content,
                                types.Content(role="user", parts=[function_response_part]),
                            ],
                        )
                        
                        print("📋 **COMPREHENSIVE ANALYSIS REPORT**")
                        print("="*60)
                        print(final_resp.text)
                        print("="*60)
                        
                        # Display sources
                        if search_data['sources']:
                            print(f"\n📚 **VERIFIED SOURCES** ({len(search_data['sources'])} total)")
                            for i, source in enumerate(search_data['sources'][:15], 1):  # Show top 15
                                print(f"{i:2d}. {source}")
                            
                            if len(search_data['sources']) > 15:
                                print(f"    ... and {len(search_data['sources']) - 15} more sources")
                        
                        break
            
            if not function_call_found:
                print("📋 **DIRECT RESPONSE**")
                print("="*40)
                print(resp.text)
                print("="*40)
                
        except Exception as e:
            print(f"❌ **ERROR**: {str(e)}")
            print("🔄 Please try rephrasing your query or check your API keys.")
            continue
        
        print(f"\n{'='*60}\n")

# Run the research session
if __name__ == "__main__":
    run_research_session()
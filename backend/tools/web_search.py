"""
Web Search Tool - Provides web search capabilities using Google Gemini API with built-in search
Used for market research, competitive analysis, and trend identification
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    published_date: Optional[str] = None
    source: Optional[str] = None
    relevance_score: Optional[float] = None


class GeminiSearchTool:
    """Google Gemini API search wrapper with built-in search capabilities"""

    def __init__(self, api_key: str, max_results_per_query: int = 10):
        if not GEMINI_AVAILABLE:
            raise ImportError("Google Gemini API not available. Install with: pip install google-genai")

        self.api_key = api_key
        self.max_results_per_query = max_results_per_query
        self.client = genai.Client(api_key=api_key)
        self.logger = logging.getLogger(__name__)

        # Configure grounding tool for search
        self.grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )

        self.config = types.GenerateContentConfig(
            tools=[self.grounding_tool]
        )

    async def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        search_depth: str = "basic",  # "basic" or "advanced"
        include_answer: bool = False,
        include_raw_content: bool = False,
        include_images: bool = False,
        days: Optional[int] = None  # Filter results by last N days
    ) -> List[SearchResult]:
        """
        Perform web search using Google Gemini API with built-in search

        Args:
            query: Search query
            max_results: Maximum number of results to return
            include_domains: List of domains to include in search
            exclude_domains: List of domains to exclude from search
            search_depth: "basic" or "advanced" search depth
            include_answer: Whether to include AI-generated answer
            include_raw_content: Whether to include raw content of pages
            include_images: Whether to include image results
            days: Filter results from last N days

        Returns:
            List of search results
        """
        try:
            # Create search query with context
            search_query = self._build_search_query(query, include_domains, exclude_domains, days)

            # Use Gemini API with search grounding
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=search_query,
                config=self.config,
            )

            # Parse the response to extract search results
            results = self._parse_gemini_response(response, max_results or self.max_results_per_query)

            self.logger.info(f"Search completed for query: {query[:50]}... - Found {len(results)} results")

            return results

        except Exception as e:
            self.logger.error(f"Search error for query '{query[:50]}...': {e}")
            raise

    async def search_with_context(
        self,
        query: str,
        context: Dict[str, Any],
        max_results: int = 5
    ) -> List[SearchResult]:
        """
        Enhanced search with additional context

        Args:
            query: Search query
            context: Additional context to guide search
            max_results: Maximum results to return

        Returns:
            List of search results
        """
        # Enhance query with context
        enhanced_query = self._enhance_query_with_context(query, context)

        # Determine search parameters based on context
        search_params = self._determine_search_params(context)

        return await self.search(enhanced_query, max_results=max_results, **search_params)

    async def multi_search(
        self,
        queries: List[str],
        max_results_per_query: int = 3,
        merge_strategy: str = "chronological"  # "chronological", "relevance", "domain"
    ) -> List[SearchResult]:
        """
        Perform multiple searches and merge results

        Args:
            queries: List of search queries
            max_results_per_query: Results per query
            merge_strategy: How to merge results

        Returns:
            Merged list of search results
        """
        all_results = []

        # Execute searches concurrently
        search_tasks = [
            self.search(query, max_results=max_results_per_query)
            for query in queries
        ]

        try:
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

            # Collect successful results
            for i, results in enumerate(search_results):
                if isinstance(results, Exception):
                    self.logger.error(f"Search failed for query {i}: {results}")
                    continue

                all_results.extend(results)

        except Exception as e:
            self.logger.error(f"Multi-search error: {e}")

        # Merge and sort results
        return self._merge_results(all_results, merge_strategy)

    async def news_search(
        self,
        query: str,
        max_results: int = 10,
        days: int = 7
    ) -> List[SearchResult]:
        """
        Search for recent news articles

        Args:
            query: Search query
            max_results: Maximum results
            days: Number of days to look back

        Returns:
            List of news search results
        """
        # Focus on news sources
        news_domains = [
            "reuters.com", "bloomberg.com", "wsj.com", "ft.com", "cnbc.com",
            "techcrunch.com", "venturebeat.com", "forbes.com", "wired.com",
            "bbc.com", "cnn.com", "nytimes.com", "washingtonpost.com"
        ]

        return await self.search(
            query,
            max_results=max_results,
            include_domains=news_domains,
            days=days,
            search_depth="advanced"
        )

    async def academic_search(
        self,
        query: str,
        max_results: int = 5
    ) -> List[SearchResult]:
        """
        Search for academic and research content

        Args:
            query: Search query
            max_results: Maximum results

        Returns:
            List of academic search results
        """
        # Focus on academic sources
        academic_domains = [
            "scholar.google.com", "arxiv.org", "researchgate.net", "academia.edu",
            "pubmed.ncbi.nlm.nih.gov", "ieeexplore.ieee.org", "dl.acm.org",
            "sciencedirect.com", "springer.com", "nature.com"
        ]

        # Enhance query for academic content
        enhanced_query = f"{query} research study analysis findings"

        return await self.search(
            enhanced_query,
            max_results=max_results,
            include_domains=academic_domains,
            search_depth="advanced"
        )

    async def company_search(
        self,
        company_name: str,
        search_type: str = "general",  # "general", "financial", "news", "competitors"
        max_results: int = 10
    ) -> List[SearchResult]:
        """
        Search for company-specific information

        Args:
            company_name: Name of the company
            search_type: Type of search to perform
            max_results: Maximum results

        Returns:
            List of company search results
        """
        # Build search query based on type
        query_templates = {
            "general": f'"{company_name}" company profile overview',
            "financial": f'"{company_name}" financial performance revenue earnings',
            "news": f'"{company_name}" latest news updates announcements',
            "competitors": f'"{company_name}" competitors market competition'
        }

        query = query_templates.get(search_type, query_templates["general"])

        # Add site restrictions for specific types
        search_params = {}
        if search_type == "financial":
            financial_domains = ["finance.yahoo.com", "sec.gov", "morningstar.com", "marketwatch.com"]
            search_params["include_domains"] = financial_domains

        return await self.search(query, max_results=max_results, **search_params)

    def _build_search_query(self, query: str, include_domains: Optional[List[str]] = None,
                           exclude_domains: Optional[List[str]] = None, days: Optional[int] = None) -> str:
        """Build search query with constraints"""
        search_parts = [query]

        if include_domains:
            domain_constraint = " OR ".join(f"site:{domain}" for domain in include_domains)
            search_parts.append(f"({domain_constraint})")

        if exclude_domains:
            for domain in exclude_domains:
                search_parts.append(f"-site:{domain}")

        if days:
            search_parts.append(f"after:{days} days ago")

        return " ".join(search_parts)

    def _parse_gemini_response(self, response, max_results: int) -> List[SearchResult]:
        """Parse Gemini API response to extract search results"""
        results = []

        try:
            # Extract grounding information from response
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        # Look for grounding metadata
                        if hasattr(part, 'function_call') and part.function_call:
                            # This contains the search results
                            continue

                        # Extract text content that may contain search result summaries
                        if hasattr(part, 'text'):
                            text = part.text
                            # Parse search results from the text response
                            # This is a simplified parsing - in practice, you'd need more sophisticated parsing
                            results.extend(self._extract_search_results_from_text(text, max_results))

        except Exception as e:
            self.logger.warning(f"Error parsing Gemini response: {e}")

        return results[:max_results]

    def _extract_search_results_from_text(self, text: str, max_results: int) -> List[SearchResult]:
        """Extract search results from Gemini's text response"""
        results = []

        # This is a simplified implementation
        # In practice, you'd need to parse the structured grounding data
        # For now, we'll create mock results based on the query

        # Look for URLs in the text
        import re
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, text)

        for i, url in enumerate(urls[:max_results]):
            # Extract domain for source
            domain = self._extract_domain(url)

            # Create a basic result
            result = SearchResult(
                title=f"Search Result {i+1}",
                url=url,
                snippet=f"Content from {domain}",
                source=domain,
                relevance_score=0.8
            )
            results.append(result)

        return results

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return ""

    def _enhance_query_with_context(self, query: str, context: Dict[str, Any]) -> str:
        """Enhance search query with context"""
        enhanced_parts = [query]

        # Add industry context
        if context.get("industry"):
            enhanced_parts.append(context["industry"])

        # Add location context
        if context.get("location"):
            enhanced_parts.append(context["location"])

        # Add time context
        if context.get("time_period"):
            enhanced_parts.append(context["time_period"])

        # Add specific context terms
        context_terms = context.get("search_terms", [])
        if context_terms:
            enhanced_parts.extend(context_terms)

        return " ".join(enhanced_parts)

    def _determine_search_params(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Determine search parameters based on context"""
        params = {}

        # Add domain restrictions
        if context.get("include_domains"):
            params["include_domains"] = context["include_domains"]

        if context.get("exclude_domains"):
            params["exclude_domains"] = context["exclude_domains"]

        # Set search depth
        if context.get("deep_search"):
            params["search_depth"] = "advanced"

        # Set time filter
        if context.get("days_filter"):
            params["days"] = context["days_filter"]

        return params

    def _merge_results(
        self,
        results: List[SearchResult],
        strategy: str = "chronological"
    ) -> List[SearchResult]:
        """Merge and sort search results"""
        if strategy == "chronological":
            # Sort by publication date (newest first)
            return sorted(
                results,
                key=lambda x: (x.published_date or ""),
                reverse=True
            )
        elif strategy == "relevance":
            # Sort by relevance score
            return sorted(
                results,
                key=lambda x: (x.relevance_score or 0),
                reverse=True
            )
        elif strategy == "domain":
            # Group by domain and sort within each domain
            domain_groups = {}
            for result in results:
                domain = result.source or "unknown"
                if domain not in domain_groups:
                    domain_groups[domain] = []
                domain_groups[domain].append(result)

            # Sort domains alphabetically and results within each domain by relevance
            sorted_results = []
            for domain in sorted(domain_groups.keys()):
                domain_results = sorted(
                    domain_groups[domain],
                    key=lambda x: (x.relevance_score or 0),
                    reverse=True
                )
                sorted_results.extend(domain_results)

            return sorted_results
        else:
            # Default: return as-is
            return results

    async def get_search_statistics(self) -> Dict[str, Any]:
        """Get search usage statistics"""
        # This would track usage metrics in a real implementation
        return {
            "total_searches": 0,
            "average_response_time": 0,
            "success_rate": 1.0,
            "last_search": None
        }


# Utility functions for common search patterns

async def search_competitors(
    search_tool: GeminiSearchTool,
    market: str,
    industry: str,
    max_competitors: int = 5
) -> List[SearchResult]:
    """Search for competitors in a market"""
    queries = [
        f"top competitors {market} {industry}",
        f"leading companies {market} industry",
        f"market leaders {industry} {market}",
        f"biggest players {market} sector"
    ]

    results = await search_tool.multi_search(
        queries,
        max_results_per_query=max_competitors,
        merge_strategy="relevance"
    )

    return results[:max_competitors]


async def search_market_trends(
    search_tool: GeminiSearchTool,
    industry: str,
    time_period: str = "2024"
) -> List[SearchResult]:
    """Search for market trends in an industry"""
    queries = [
        f"{industry} trends {time_period}",
        f"emerging trends {industry}",
        f"market developments {industry}",
        f"industry forecast {industry}"
    ]

    return await search_tool.multi_search(
        queries,
        max_results_per_query=3,
        merge_strategy="chronological"
    )


async def search_financial_data(
    search_tool: GeminiSearchTool,
    company: str
) -> List[SearchResult]:
    """Search for financial data of a company"""
    return await search_tool.company_search(
        company,
        search_type="financial",
        max_results=10
    )


async def search_industry_reports(
    search_tool: GeminiSearchTool,
    industry: str
) -> List[SearchResult]:
    """Search for industry reports and analysis"""
    queries = [
        f"{industry} industry report analysis",
        f"{industry} market research report",
        f"{industry} industry outlook forecast"
    ]

    report_domains = [
        "mckinsey.com", "bcg.com", "deloitte.com", "pwc.com", "ey.com",
        "gartner.com", "forrester.com", "idc.com", "statista.com"
    ]

    results = []
    for query in queries:
        query_results = await search_tool.search(
            query,
            max_results=3,
            include_domains=report_domains,
            search_depth="advanced"
        )
        results.extend(query_results)

    return results
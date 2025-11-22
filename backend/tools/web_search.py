"""
Web Search Tool - Provides web search capabilities using Tavily API
Used for market research, competitive analysis, and trend identification
"""

import asyncio
import aiohttp
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    published_date: Optional[str] = None
    source: Optional[str] = None
    relevance_score: Optional[float] = None


class TavilySearchTool:
    """Tavily search API wrapper for web searching"""

    def __init__(self, api_key: str, max_results_per_query: int = 10):
        self.api_key = api_key
        self.max_results_per_query = max_results_per_query
        self.base_url = "https://api.tavily.com/search"
        self.logger = logging.getLogger(__name__)
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

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
        Perform web search using Tavily API

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
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            # Prepare search parameters
            params = {
                "api_key": self.api_key,
                "query": query,
                "search_depth": search_depth,
                "include_answer": include_answer,
                "include_raw_content": include_raw_content,
                "include_images": include_images,
                "max_results": max_results or self.max_results_per_query
            }

            # Add optional parameters
            if include_domains:
                params["include_domains"] = include_domains

            if exclude_domains:
                params["exclude_domains"] = exclude_domains

            if days:
                # Calculate date threshold
                from datetime import datetime, timedelta
                date_threshold = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
                params["include_raw_content"] = True  # Enable raw content for date filtering

            # Make API request
            async with self.session.post(
                self.base_url,
                json=params,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:

                if response.status != 200:
                    error_text = await response.text()
                    self.logger.error(f"Tavily API error: {response.status} - {error_text}")
                    raise Exception(f"Search API error: {response.status}")

                data = await response.json()

                # Process results
                results = []
                if "results" in data:
                    for item in data["results"]:
                        # Apply date filtering if specified
                        if days and item.get("published_date"):
                            try:
                                pub_date = datetime.fromisoformat(item["published_date"].replace("Z", "+00:00"))
                                cutoff_date = datetime.now() - timedelta(days=days)
                                if pub_date < cutoff_date:
                                    continue
                            except:
                                # If date parsing fails, include the result
                                pass

                        result = SearchResult(
                            title=item.get("title", ""),
                            url=item.get("url", ""),
                            snippet=item.get("content", ""),
                            published_date=item.get("published_date"),
                            source=self._extract_domain(item.get("url", "")),
                            relevance_score=item.get("score")
                        )
                        results.append(result)

                self.logger.info(f"Search completed for query: {query[:50]}... - Found {len(results)} results")

                # Filter by max results again (in case API returned more)
                return results[: (max_results or self.max_results_per_query)]

        except asyncio.TimeoutError:
            self.logger.error(f"Search timeout for query: {query[:50]}...")
            raise Exception("Search request timed out")

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
    search_tool: TavilySearchTool,
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
    search_tool: TavilySearchTool,
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
    search_tool: TavilySearchTool,
    company: str
) -> List[SearchResult]:
    """Search for financial data of a company"""
    return await search_tool.company_search(
        company,
        search_type="financial",
        max_results=10
    )


async def search_industry_reports(
    search_tool: TavilySearchTool,
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
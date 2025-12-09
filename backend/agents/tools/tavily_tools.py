"""
Tavily search integration tools for AutoAdmin agents.

This module provides search capabilities for research, market analysis,
and competitive intelligence gathering using the Tavily API.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from tavily import TavilyClient


@dataclass
class SearchResult:
    """Represents a search result from Tavily."""
    title: str
    url: str
    content: str
    score: Optional[float] = None
    published_date: Optional[str] = None
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'url': self.url,
            'content': self.content,
            'score': self.score,
            'published_date': self.published_date,
            'source': self.source
        }


logger = logging.getLogger(__name__)


class TavilySearchTools:
    """
    Collection of search tools using Tavily API for various research tasks.

    Provides specialized search functions for market research, competitive analysis,
    trend detection, and content generation research.
    """

    def __init__(self, api_key: str):
        """Initialize Tavily search client."""
        self.client = TavilyClient(api_key=api_key)

    async def search_market_trends(self, industry: str, time_range: str = "week", max_results: int = 10) -> List[SearchResult]:
        """
        Search for market trends in a specific industry.

        Args:
            industry: Industry to search for trends
            time_range: Time range for trends ('day', 'week', 'month', 'year')
            max_results: Maximum number of results

        Returns:
            List of trend-related search results
        """
        try:
            query = f"latest trends {industry} market analysis {time_range}"

            response = self.client.search(
                query=query,
                search_depth="advanced",
                include_domains=None,
                max_results=max_results,
                include_answer=True,
                include_raw_content=False,
                include_images=False
            )

            results = []
            for item in response.get('results', []):
                result = SearchResult(
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    content=item.get('content', ''),
                    score=item.get('score'),
                    published_date=item.get('published_date'),
                    source=item.get('source', 'web')
                )
                results.append(result)

            logger.info(f"Found {len(results)} market trends for {industry}")
            return results

        except Exception as e:
            logger.error(f"Error searching market trends: {str(e)}")
            return []

    async def search_competitors(self, company: str, max_results: int = 15) -> List[SearchResult]:
        """
        Search for competitor information and analysis.

        Args:
            company: Company name to analyze competitors for
            max_results: Maximum number of results

        Returns:
            List of competitor-related search results
        """
        try:
            query = f"{company} competitors analysis market share alternatives"

            response = self.client.search(
                query=query,
                search_depth="advanced",
                include_domains=None,
                max_results=max_results,
                include_answer=True,
                include_raw_content=False
            )

            results = []
            for item in response.get('results', []):
                result = SearchResult(
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    content=item.get('content', ''),
                    score=item.get('score'),
                    published_date=item.get('published_date'),
                    source=item.get('source', 'web')
                )
                results.append(result)

            logger.info(f"Found {len(results)} competitor results for {company}")
            return results

        except Exception as e:
            logger.error(f"Error searching competitors: {str(e)}")
            return []

    async def search_technology_trends(self, technology: str, max_results: int = 10) -> List[SearchResult]:
        """
        Search for technology trends and developments.

        Args:
            technology: Technology or programming language to search for
            max_results: Maximum number of results

        Returns:
            List of technology trend search results
        """
        try:
            query = f"latest trends {technology} 2024 2025 developments updates"

            response = self.client.search(
                query=query,
                search_depth="advanced",
                include_domains=None,
                max_results=max_results,
                include_answer=True,
                include_raw_content=False
            )

            results = []
            for item in response.get('results', []):
                result = SearchResult(
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    content=item.get('content', ''),
                    score=item.get('score'),
                    published_date=item.get('published_date'),
                    source=item.get('source', 'web')
                )
                results.append(result)

            logger.info(f"Found {len(results)} technology trends for {technology}")
            return results

        except Exception as e:
            logger.error(f"Error searching technology trends: {str(e)}")
            return []

    async def search_content_ideas(self, topic: str, content_type: str = "blog", max_results: int = 8) -> List[SearchResult]:
        """
        Search for content ideas and research for a given topic.

        Args:
            topic: Topic to generate content ideas for
            content_type: Type of content ('blog', 'video', 'social', 'podcast')
            max_results: Maximum number of results

        Returns:
            List of content idea search results
        """
        try:
            query = f"{content_type} content ideas {topic} research outline"

            response = self.client.search(
                query=query,
                search_depth="advanced",
                include_domains=None,
                max_results=max_results,
                include_answer=True,
                include_raw_content=False
            )

            results = []
            for item in response.get('results', []):
                result = SearchResult(
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    content=item.get('content', ''),
                    score=item.get('score'),
                    published_date=item.get('published_date'),
                    source=item.get('source', 'web')
                )
                results.append(result)

            logger.info(f"Found {len(results)} content ideas for {topic}")
            return results

        except Exception as e:
            logger.error(f"Error searching content ideas: {str(e)}")
            return []

    async def search_financial_data(self, company: str, data_type: str = "stocks") -> List[SearchResult]:
        """
        Search for financial data and analysis.

        Args:
            company: Company to search financial data for
            data_type: Type of financial data ('stocks', 'earnings', 'revenue', 'analysis')
            max_results: Maximum number of results

        Returns:
            List of financial data search results
        """
        try:
            query = f"{company} {data_type} financial analysis performance metrics"

            response = self.client.search(
                query=query,
                search_depth="advanced",
                include_domains=[
                    'finance.yahoo.com',
                    'sec.gov',
                    'marketwatch.com',
                    'reuters.com',
                    'bloomberg.com'
                ],
                max_results=8,
                include_answer=True,
                include_raw_content=False
            )

            results = []
            for item in response.get('results', []):
                result = SearchResult(
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    content=item.get('content', ''),
                    score=item.get('score'),
                    published_date=item.get('published_date'),
                    source=item.get('source', 'web')
                )
                results.append(result)

            logger.info(f"Found {len(results)} financial data results for {company}")
            return results

        except Exception as e:
            logger.error(f"Error searching financial data: {str(e)}")
            return []

    async def search_news_updates(self, topic: str, time_range: str = "day") -> List[SearchResult]:
        """
        Search for recent news updates on a topic.

        Args:
            topic: Topic to search news for
            time_range: Time range ('hour', 'day', 'week')
            max_results: Maximum number of results

        Returns:
            List of news search results
        """
        try:
            query = f"latest news {topic} {time_range}"

            response = self.client.search(
                query=query,
                search_depth="advanced",
                include_domains=[
                    'news.google.com',
                    'news.yahoo.com',
                    'reuters.com',
                    'apnews.com',
                    'bbc.com',
                    'cnn.com'
                ],
                max_results=12,
                include_answer=True,
                include_raw_content=False
            )

            results = []
            for item in response.get('results', []):
                result = SearchResult(
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    content=item.get('content', ''),
                    score=item.get('score'),
                    published_date=item.get('published_date'),
                    source=item.get('source', 'web')
                )
                results.append(result)

            logger.info(f"Found {len(results)} news updates for {topic}")
            return results

        except Exception as e:
            logger.error(f"Error searching news updates: {str(e)}")
            return []

    async def comprehensive_research(self, topic: str, research_depth: str = "standard") -> Dict[str, List[SearchResult]]:
        """
        Perform comprehensive research on a topic across multiple dimensions.

        Args:
            topic: Topic to research
            research_depth: Depth of research ('quick', 'standard', 'deep')

        Returns:
            Dictionary with categorized research results
        """
        try:
            max_results = 5 if research_depth == "quick" else (8 if research_depth == "standard" else 15)

            # Parallel search across different categories
            results = {
                'trends': await self.search_technology_trends(topic, max_results),
                'news': await self.search_news_updates(topic, "week"),
                'analysis': await self.search_market_trends(topic, "month", max_results),
                'content_ideas': await self.search_content_ideas(topic, "blog", max_results)
            }

            total_results = sum(len(category_results) for category_results in results.values())
            logger.info(f"Comprehensive research for {topic}: {total_results} total results across {len(results)} categories")

            return results

        except Exception as e:
            logger.error(f"Error in comprehensive research: {str(e)}")
            return {
                'trends': [],
                'news': [],
                'analysis': [],
                'content_ideas': []
            }

    async def extract_insights(self, search_results: List[SearchResult]) -> List[str]:
        """
        Extract key insights from search results.

        Args:
            search_results: List of search results to analyze

        Returns:
            List of extracted insights
        """
        try:
            if not search_results:
                return []

            # Simple insight extraction based on content analysis
            insights = []

            # Group by content themes
            content_themes = {}
            for result in search_results:
                # Extract key phrases and themes (simplified version)
                content_lower = result.content.lower()

                # Look for trend indicators
                if any(word in content_lower for word in ['trend', 'increase', 'growth', 'rising']):
                    insights.append(f"Trend indicated: {result.title[:100]}...")

                # Look for technology mentions
                if any(tech in content_lower for tech in ['ai', 'machine learning', 'automation', 'python']):
                    insights.append(f"Technology focus: {result.title[:100]}...")

                # Look for business impact
                if any(word in content_lower for word in ['revenue', 'profit', 'market', 'business']):
                    insights.append(f"Business impact: {result.title[:100]}...")

            return insights[:10]  # Limit to top 10 insights

        except Exception as e:
            logger.error(f"Error extracting insights: {str(e)}")
            return []
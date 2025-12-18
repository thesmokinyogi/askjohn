#!/usr/bin/env python3
# COGSPACE v40.0.0
"""
COGSPACE Revolution v20.0.0 - Research Fetcher
Brilliant Binary Speed Implementation by Bob
Mission Critical: Multi-source research aggregation
"""

import sys
import json
import requests
from datetime import datetime
from typing import List, Dict, Any

#═══════════════════════════════════════════════════════════════════════════════
# RESEARCH SOURCES - Free Tier APIs
#═══════════════════════════════════════════════════════════════════════════════

class ResearchFetcher:
    def __init__(self, technology: str, query: str):
        self.technology = technology
        self.query = query
        self.sources = []
        self.timeout = 10  # seconds

    def fetch_all(self) -> Dict[str, Any]:
        """Fetch research from all sources"""
        # Try each source (graceful fallback on failures)
        self._fetch_github()
        self._fetch_stackoverflow()

        # Build result
        result = {
            "technology": self.technology,
            "query": self.query,
            "sources": self.sources,
            "cached": False,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        return result

    def _fetch_github(self):
        """Fetch code examples from GitHub"""
        try:
            # GitHub public API search
            url = "https://api.github.com/search/repositories"
            params = {
                "q": f"{self.technology} {self.query} stars:>100",
                "sort": "stars",
                "order": "desc",
                "per_page": 3
            }

            response = requests.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()

                for repo in data.get("items", [])[:3]:
                    self.sources.append({
                        "type": "github_example",
                        "title": repo["full_name"],
                        "url": repo["html_url"],
                        "stars": repo["stargazers_count"],
                        "relevance": 0.90,
                        "description": repo.get("description", "")[:200]
                    })
        except Exception as e:
            # Graceful failure
            pass

    def _fetch_stackoverflow(self):
        """Fetch community solutions from Stack Overflow"""
        try:
            # Stack Exchange API (no auth required)
            url = "https://api.stackexchange.com/2.3/search/advanced"
            params = {
                "order": "desc",
                "sort": "votes",
                "q": f"{self.technology} {self.query}",
                "site": "stackoverflow",
                "pagesize": 3
            }

            response = requests.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()

                for question in data.get("items", [])[:3]:
                    self.sources.append({
                        "type": "stackoverflow",
                        "title": question["title"],
                        "url": question["link"],
                        "votes": question.get("score", 0),
                        "relevance": 0.75,
                        "answered": question.get("is_answered", False)
                    })
        except Exception as e:
            # Graceful failure
            pass

    def _fetch_semantic_scholar(self):
        """Fetch academic papers (optional - may timeout)"""
        try:
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                "query": f"{self.technology} {self.query}",
                "limit": 3,
                "fields": "title,url,citationCount,abstract"
            }

            response = requests.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()

                for paper in data.get("data", [])[:3]:
                    self.sources.append({
                        "type": "research_paper",
                        "title": paper.get("title", ""),
                        "url": paper.get("url", ""),
                        "citations": paper.get("citationCount", 0),
                        "relevance": 0.70,
                        "abstract": paper.get("abstract", "")[:300]
                    })
        except Exception as e:
            # Graceful failure - academic papers are bonus, not required
            pass

#═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
#═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: fetch-research.py <technology> [query]"}))
        sys.exit(1)

    technology = sys.argv[1]
    query = sys.argv[2] if len(sys.argv) > 2 else "best practices"

    fetcher = ResearchFetcher(technology, query)
    result = fetcher.fetch_all()

    print(json.dumps(result, indent=2))


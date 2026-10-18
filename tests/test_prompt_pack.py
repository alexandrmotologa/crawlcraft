"""Unit tests for the LLM prompt context packaging engine."""

import pytest
from crawlcraft.core.crawler import CrawledPage
from crawlcraft.extractor.metadata import PageMetadata
from crawlcraft.extractor.prompt_pack import pack_pages_for_llm


def test_pack_pages_xml_format():
    meta1 = PageMetadata(
        title="Installation Guide",
        description="How to install CrawlCraft",
        token_stats={"token_count": 120, "word_count": 80},
    )
    page1 = CrawledPage(
        url="https://example.com/install",
        depth=0,
        status_code=200,
        rendered_with="http2",
        markdown="Run `pip install crawlcraft` to begin.",
        metadata=meta1,
    )

    meta2 = PageMetadata(
        title="Architecture Overview",
        description="Internal architecture and benchmarks",
        token_stats={"token_count": 350, "word_count": 220},
    )
    page2 = CrawledPage(
        url="https://example.com/arch",
        depth=1,
        status_code=200,
        rendered_with="selectolax",
        markdown="## Internal Design\nSelectolax Lexbor C engine.",
        metadata=meta2,
    )

    xml_output = pack_pages_for_llm(
        [page1, page2],
        format_type="xml",
        system_directive="You are a senior technical advisor with access to the following documentation.",
    )

    assert "<system_context>" in xml_output
    assert "You are a senior technical advisor" in xml_output
    assert '<knowledge_base total_documents="2" total_tokens="470">' in xml_output
    assert "<manifest>" in xml_output
    assert '<entry id="1" url="https://example.com/install" title="Installation Guide" tokens="120" />' in xml_output
    assert '<entry id="2" url="https://example.com/arch" title="Architecture Overview" tokens="350" />' in xml_output
    assert '<document id="1" url="https://example.com/install"' in xml_output
    assert "<![CDATA[\nRun `pip install crawlcraft` to begin.\n    ]]>" in xml_output


def test_pack_pages_markdown_format():
    dict_pages = [
        {
            "url": "https://example.com/quickstart",
            "metadata": {
                "title": "Quickstart Guide",
                "description": "5-minute introduction",
                "token_stats": {"token_count": 90},
            },
            "markdown": "# Quickstart\nStart scraping immediately.",
        }
    ]

    md_output = pack_pages_for_llm(
        dict_pages,
        format_type="markdown",
        system_directive="Answer solely based on the documents below.",
    )

    assert "System Instructions:" in md_output
    assert "# Knowledge Base (1 Documents | 90 Tokens)" in md_output
    assert "| 1 | Quickstart Guide | https://example.com/quickstart | 90 |" in md_output
    assert "## Document 1: Quickstart Guide" in md_output
    assert "Start scraping immediately." in md_output

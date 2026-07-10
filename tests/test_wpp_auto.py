from demografia.wpp_auto import discover_wpp_age_sex_urls


def test_wpp_discovery_prefers_single_age_file():
    html = """
    <a href="files/WPP2024_PopulationByAge5GroupSex_Medium.csv.gz">five</a>
    <a href="files/WPP2024_PopulationBySingleAgeSex_Medium_1950-2100.csv.gz">single</a>
    """
    urls = discover_wpp_age_sex_urls(html)
    assert "SingleAgeSex" in urls[0]
    assert all(url.startswith("https://population.un.org/") for url in urls)

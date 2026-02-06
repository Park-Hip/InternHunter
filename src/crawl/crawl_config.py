import os

from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

# Production: headless + quiet. Override for local debug: CRAWL_HEADLESS=0 CRAWL_VERBOSE=1
HEADLESS = os.getenv("CRAWL_HEADLESS", "true").lower() in ("1", "true", "yes")
VERBOSE = os.getenv("CRAWL_VERBOSE", "false").lower() in ("1", "true", "yes")

# Run schema for fetching links process
fetch_link_schema = {
        "name": "Job Links",
        "baseSelector": ".job-item-search-result",
        "fields": [
            {
                "name": "url",
                "selector": "h3.title a",
                "type": "attribute",
                "attribute": "href"
            }
        ]
    }

fetch_link_run_config = CrawlerRunConfig(
    extraction_strategy=JsonCssExtractionStrategy(fetch_link_schema),
    cache_mode=CacheMode.BYPASS,
    wait_for="css:.job-item-search-result",
    page_timeout=30000
)

# Run schema for extracting single job details
extract_detail_schema = {
    "name": "TopCV Extraction",
    "baseSelector": "html",
    "fields": [
        {
            "name": "title",
            "selector": (
                "h1, "                                                 
                ".job-detail__info--title, "                            
                ".job-detail-title, "                                   
                ".title-job, "                                          
                ".premium-job-basic-information__content--title a, "   
                "h2.title, "                                            
                "h2.title:has(.icon-verified-employer)"  
                "#header-job-info h2, "   
                "title"           
            ),
            "type": "text"
        },
        {
            "name": "company",
            "selector": (
                ".company-name-label a, "      
                ".company-content__title--name, "
                ".box-info-job .company-title, "
                "a.company-name, "              
                ".sidebar-brand-name, "          
                ".box-company-name, "           
                ".company-name, "   
                ".breadcrumb li:nth-last-child(2) a, "
                "title"              
            ),
            "type": "text"
        },
        {
            "name": "salary",
            "selector": (
                ".section-salary .job-detail__info--section-content-value, " 
                ".box-item:has(.fa-money-bill-wave) span, "                  
                ".box-item:has(.fa-sack-dollar) span"                       
            ),
            "type": "text"
        },
        {
            "name": "location",
            "selector": (
                ".section-location .job-detail__info--section-content-value, " 
                ".box-item:has(.fa-location-dot) span, "                       
                ".box-item:has(.fa-map-marker-alt) span"                    
            ),
            "type": "text"
        },
        {
            "name": "experience",
            "selector": (
                "#job-detail-info-experience .job-detail__info--section-content-value, " 
                ".box-item:has(.fa-star) span"                                           
            ),
            "type": "text"
        },
        {
            "name": "info",
            "selector": (
                ".job-description, "                       
                ".premium-job-description__box--content, " 
                ".content-tab, "   
                "#box-job-information"                         
            ),
            "type": "text"
        },
    ]
}


extraction_strategy = JsonCssExtractionStrategy(extract_detail_schema)
# css_selector_filter = "#header-job-info, .box-main, .job-detail__box--right, .job-description, .box-info-job"

extract_detail_run_config = CrawlerRunConfig(
    extraction_strategy=extraction_strategy,
    # cache_mode=CacheMode.ENABLED,
    cache_mode=CacheMode.BYPASS,
    magic=True,
    simulate_user=True,
    page_timeout=30000,
    delay_before_return_html=3.0,
    wait_for="css:h1, h2.title, .job-detail-title", ##
    word_count_threshold=5,
    remove_overlay_elements=False,
    exclude_external_links=True,
)

# Browser config (headless/verbose from env for production safety)
browser_config = BrowserConfig(
    headless=HEADLESS,
    verbose=VERBOSE,
    user_agent_mode="random",
)



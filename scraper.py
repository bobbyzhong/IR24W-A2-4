import re
from urllib.parse import urldefrag, urlparse
from collections import Counter
from bs4 import BeautifulSoup
import time
from urllib.robotparser import RobotFileParser
import logging

class PolitenessManager:
    def __init__(self):
        self.last_access = {}

    def can_access(self, url):
        domain = urlparse(url).netloc
        current_time = time.time()
        if domain not in self.last_access:
            self.last_access[domain] = current_time
            return True
        else:
            politeness_delay = self.get_politeness_delay(url)
            if current_time - self.last_access[domain] >= politeness_delay:
                self.last_access[domain] = current_time
                return True
            else:
                return False

    def get_politeness_delay(self, url):
        domain = urlparse(url).netloc
        # Fetch and parse robots.txt for the domain
        rp = RobotFileParser()
        rp.set_url(f"http://{domain}/robots.txt")
        rp.read()
        return rp.crawl_delay("*") or 0

class TrapDetector:
    def __init__(self):
        self.visited_urls = set()

    def detect_trap(self, url):
        if url in self.visited_urls:
            return True
        else:
            self.visited_urls.add(url)
            return False

def scraper(url, resp):
    politeness_manager = PolitenessManager()
    trap_detector = TrapDetector()

    if politeness_manager.can_access(url) and not trap_detector.detect_trap(url) and is_valid(url):
        links = extract_next_links(url, resp)
        crawled_pages = crawl_pages(url, resp)
        log_stats(crawled_pages)
        return links
    else:
        return []

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    links = set()
    # Check if the response status is 200 (OK)
    if resp.status == 200:
        # Create a BeautifulSoup object to parse the HTML content
        soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
        # Find all anchor tags in the HTML content
        anchor_tags = soup.find_all('a', href=True)
        for tag in anchor_tags:
            link = tag['href']
            # Normalize the URL and add it to the set of links
            normalized_link = normalize(link)
            if is_valid(normalized_link):
                links.add(normalized_link)
    return list(links)


def count_words(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    # Remove HTML markup and extract text
    text = soup.get_text()
    # Count words
    words = re.findall(r'\b\w+\b', text)
    return len(words)

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False

        domain = parsed.netloc.lower()
        allowed_domains = [
            "ics.uci.edu",
            "cs.uci.edu",
            "informatics.uci.edu",
            "stat.uci.edu"
        ]
        if any(domain.endswith(subdomain) for subdomain in allowed_domains):
            return not re.match(
                r".*\.(css|js|bmp|gif|jpe?g|ico"
                + r"|png|tiff?|mid|mp2|mp3|mp4"
                + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
                + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
                + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
                + r"|epub|dll|cnf|tgz|sha1"
                + r"|thmx|mso|arff|rtf|jar|csv"
                + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())
        else:
            return False


    except TypeError:
        print ("TypeError for ", parsed)
        raise

def normalize(url):
    # Perform URL normalization here (if needed)
    return url

def get_unique_pages_count(crawled_pages):
    unique_pages = set()
    for page_url, _ in crawled_pages:
        # Remove fragment part of the URL
        url_without_fragment = urldefrag(page_url)[0]
        unique_pages.add(url_without_fragment)
    return len(unique_pages)

def get_longest_page(crawled_pages):
    longest_page = max(crawled_pages, key=lambda x: x[1])
    return longest_page

def get_common_words(crawled_pages):
    all_text = b""
    for _, html_content in crawled_pages:
        all_text += html_content  # Accumulate bytes content
    soup = BeautifulSoup(all_text, 'html.parser')
    # Remove HTML markup and extract text
    text = soup.get_text()
    # Count occurrences of each word
    words = re.findall(r'\b\w+\b', text.lower())
    # Load English stop words
    with open('english_stopwords.txt', 'r') as f:
        stop_words = set(f.read().splitlines())
    # Filter out stop words
    filtered_words = [word for word in words if word not in stop_words]
    # Count occurrences of each word
    word_counts = Counter(filtered_words)
    # Get the 50 most common words
    most_common_words = word_counts.most_common(50)
    return most_common_words

def get_subdomains_info(crawled_pages):
    subdomains_info = {}
    allowed_domains = [
        "ics.uci.edu",
        "cs.uci.edu",
        "informatics.uci.edu",
        "stat.uci.edu"
    ]
    for page_url, _ in crawled_pages:
        parsed_url = urlparse(page_url)
        domain = parsed_url.netloc
        for allowed_domain in allowed_domains:
            if domain.endswith(allowed_domain):
                subdomain = parsed_url.hostname.split(".", 1)[0]
                subdomains_info[subdomain] = subdomains_info.get(subdomain, 0) + 1
                break  # No need to check other allowed domains
    sorted_subdomains_info = sorted(subdomains_info.items(), key=lambda x: x[0])
    return sorted_subdomains_info

def log_unique_pages_count(crawled_pages):
    unique_pages_count = get_unique_pages_count(crawled_pages)
    logging.info(f"Number of unique pages found: {unique_pages_count}")

def log_longest_page(crawled_pages):
    longest_page = get_longest_page(crawled_pages)
    logging.info(f"Longest page number of words: ({longest_page[0]} words)")

def log_common_words(crawled_pages):
    common_words = get_common_words(crawled_pages)
    logging.info("50 most common words:")
    for word, count in common_words:
        logging.info(f"{word}: {count}")

def log_subdomains_info(crawled_pages):
    subdomains_info = get_subdomains_info(crawled_pages)
    logging.info("Subdomains and the number of unique pages detected in each subdomain:")
    for subdomain, num_pages in subdomains_info:
        logging.info(f"{subdomain}: {num_pages} unique pages")

# Modify the crawl_pages function to return crawled pages
def crawl_pages(url, resp):
    # Implement your crawling logic here
    crawled_pages = []
    if resp is not None:
        if resp.status==200 and resp.raw_response is not None:
            num_words = count_words(resp.raw_response.content)
            crawled_pages.append((url, resp.raw_response.content))
            # Log progress
            logging.info(f"Crawled {url}, found {num_words} words")
    return crawled_pages


def log_stats(crawled_pages):
    if not crawled_pages:
        logging.info("No pages were crawled.")
        return
    log_longest_page(crawled_pages)
    log_common_words(crawled_pages)
    log_subdomains_info(crawled_pages)
    log_unique_pages_count(crawled_pages)
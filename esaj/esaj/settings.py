# Scrapy settings for esaj project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import logging
import os
import sys

BOT_NAME = "esaj"

SPIDER_MODULES = ["esaj.spiders"]
NEWSPIDER_MODULE = "esaj.spiders"

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = "esaj (+http://www.yourdomain.com)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN = 16
#CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#    "Accept-Language": "en",
#}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    "esaj.middlewares.EsajSpiderMiddleware": 543,
#}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#DOWNLOADER_MIDDLEWARES = {
#    "esaj.middlewares.EsajDownloaderMiddleware": 543,
#}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
#}

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
#ITEM_PIPELINES = {
#    "esaj.pipelines.EsajPipeline": 300,
#}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
AUTOTHROTTLE_START_DELAY = 3
# The maximum download delay to be set in case of high latencies
AUTOTHROTTLE_MAX_DELAY = 180
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = "httpcache"
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

DOWNLOADER_MIDDLEWARES = {
    'esaj.middlewares.PdfDownloadDelayMiddleware': 543,
}

PDF_DOWNLOAD_DELAY = 3.0

LOG_ENABLED = True
LOG_LEVEL = 'WARNING'
LOG_FILE = 'scrapy.log'

logging.basicConfig(level=logging.ERROR)

info_logger = logging.getLogger('info_logger')
info_handler = logging.FileHandler('scrapy_info.log')
info_handler.setLevel(logging.INFO)

info_handler_stdout = logging.StreamHandler(sys.stdout)
info_handler_stdout.setLevel(logging.INFO)

info_logger.addHandler(info_handler)
info_logger.addHandler(info_handler_stdout)

warning_logger = logging.getLogger('warning_logger')
warning_handler = logging.FileHandler('scrapy_warnings.log')
warning_handler.setLevel(logging.WARNING)

warning_handler_stdout = logging.StreamHandler(sys.stderr)
warning_handler_stdout.setLevel(logging.WARNING)

warning_logger.addHandler(warning_handler)
warning_logger.addHandler(warning_handler_stdout)

error_logger = logging.getLogger('error_logger')
error_handler = logging.FileHandler('scrapy_errors.log')
error_handler.setLevel(logging.ERROR)

error_handler_stdout = logging.StreamHandler(sys.stderr)
error_handler_stdout.setLevel(logging.ERROR)

error_logger.addHandler(error_handler)

from enum import Enum
from dataclasses import dataclass
from typing import Dict
from datetime import datetime
import asyncio
import random
import logging
import json

from playwright.async_api import TimeoutError as PlaywrightTimeout
import aiohttp

from config.proxy_loader import MAX_RETRIES_PER_PROXY
from core.performance_monitor import performance_monitor
from core.logger import logger

class ErrorType(Enum):
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    CAPTCHA_ERROR = "captcha_error"
    PROXY_ERROR = "proxy_error"
    BROWSER_ERROR = "browser_error"
    PAGE_ERROR = "page_error"
    UNKNOWN_ERROR = "unknown_error"

@dataclass
class ErrorContext:
    error_type: ErrorType
    message: str
    function_name: str
    target_domain: str = None
    proxy: str = None
    device: str = None
    search_engine: str = None
    url: str = None
    retry_count: int = 0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class ErrorHandler:
    def __init__(self):
        self.retry_config = {
            ErrorType.NETWORK_ERROR: {'max_retries': 3, 'base_delay': 2},
            ErrorType.TIMEOUT_ERROR: {'max_retries': 2, 'base_delay': 5},
            ErrorType.CAPTCHA_ERROR: {'max_retries': 1, 'base_delay': 10},
            ErrorType.PROXY_ERROR: {'max_retries': 2, 'base_delay': 3},
            ErrorType.BROWSER_ERROR: {'max_retries': 2, 'base_delay': 1},
            ErrorType.PAGE_ERROR: {'max_retries': 2, 'base_delay': 2},
            ErrorType.UNKNOWN_ERROR: {'max_retries': 1, 'base_delay': 1}
        }
    
    def classify_error(self, error: Exception, context: Dict = None) -> ErrorType:
        error_str = str(error).lower()
        if isinstance(error, asyncio.TimeoutError) or 'timeout' in error_str:
            return ErrorType.TIMEOUT_ERROR
        elif isinstance(error, aiohttp.ClientError) or 'connection' in error_str:
            return ErrorType.NETWORK_ERROR
        elif 'captcha' in error_str or 'robot' in error_str:
            return ErrorType.CAPTCHA_ERROR
        elif 'proxy' in error_str:
            return ErrorType.PROXY_ERROR
        elif isinstance(error, PlaywrightTimeout) or 'playwright' in str(type(error)).lower():
            return ErrorType.BROWSER_ERROR
        elif 'page' in error_str or 'navigation' in error_str:
            return ErrorType.PAGE_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR
    
    async def execute_with_retry(self, func, *args, **kwargs):
        context = kwargs.pop('error_context', {})
        
        for attempt in range(MAX_RETRIES_PER_PROXY):
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"✅ موفق در تلاش {attempt + 1} برای {context.get('function_name', func.__name__)}")
                return result
                
            except Exception as e:
                error_type = self.classify_error(e, context)
                retry_config = self.retry_config.get(error_type, {'max_retries': 1, 'base_delay': 1})
                
                error_context = ErrorContext(
                    error_type=error_type,
                    message=str(e),
                    function_name=func.__name__,
                    retry_count=attempt + 1,
                    **context
                )
                
                if attempt < retry_config['max_retries'] - 1:
                    delay = retry_config['base_delay'] * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"⚠️ تلاش {attempt + 1} ناموفق برای {func.__name__}. خطا: {e}. تلاش مجدد پس از {delay:.1f} ثانیه...")
                    
                    performance_monitor.record_error(f"{error_type.value}: {str(e)}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"❌ تمام تلاش‌ها برای {func.__name__} ناموفق بود. آخرین خطا: {e}")
                    self.log_error(error_context)
                    performance_monitor.record_error(f"{error_type.value}: {str(e)}")
                    raise
        
        return None
    
    def log_error(self, context: ErrorContext):
        error_log = {
            'timestamp': context.timestamp.isoformat(),
            'error_type': context.error_type.value,
            'function': context.function_name,
            'message': context.message,
            'retry_count': context.retry_count,
            'target_domain': context.target_domain,
            'proxy': context.proxy,
            'device': context.device,
            'search_engine': context.search_engine,
            'url': context.url
        }
        
        logger.error(f"📊 خطای ثبت شده: {json.dumps(error_log, ensure_ascii=False)}")

global_error_handler = ErrorHandler()
from datetime import datetime
import json

from core.logger import logger

class PerformanceMonitor:
    def __init__(self):
        self.stats = {
            'total_searches': 0,
            'successful_searches': 0,
            'failed_searches': 0,
            'total_visits': 0,
            'successful_visits': 0,
            'failed_visits': 0,
            'proxy_failures': 0,
            'captcha_encounters': 0,
            'start_time': datetime.now(),
            'errors': []
        }
        self.search_times = []
        self.visit_times = []
    
    def record_search(self, success: bool, duration: float = None):
        self.stats['total_searches'] += 1
        if success:
            self.stats['successful_searches'] += 1
            if duration:
                self.search_times.append(duration)
        else:
            self.stats['failed_searches'] += 1
    
    def record_visit(self, success: bool, duration: float = None):
        self.stats['total_visits'] += 1
        if success:
            self.stats['successful_visits'] += 1
            if duration:
                self.visit_times.append(duration)
        else:
            self.stats['failed_visits'] += 1
    
    def record_proxy_failure(self):
        self.stats['proxy_failures'] += 1
    
    def record_captcha(self):
        self.stats['captcha_encounters'] += 1
    
    def record_error(self, error: str):
        self.stats['errors'].append({
            'timestamp': datetime.now(),
            'error': error
        })
    
    def get_summary(self) -> dict:
        runtime = (datetime.now() - self.stats['start_time']).total_seconds() / 60
        avg_search_time = sum(self.search_times) / len(self.search_times) if self.search_times else 0
        avg_visit_time = sum(self.visit_times) / len(self.visit_times) if self.visit_times else 0
        
        return {
            'runtime_minutes': runtime,
            'search_success_rate': (self.stats['successful_searches'] / max(self.stats['total_searches'], 1)) * 100,
            'visit_success_rate': (self.stats['successful_visits'] / max(self.stats['total_visits'], 1)) * 100,
            'avg_search_time': avg_search_time,
            'avg_visit_time': avg_visit_time,
            'total_errors': len(self.stats['errors']),
            'proxy_failure_rate': (self.stats['proxy_failures'] / max(self.stats['total_searches'], 1)) * 100,
            'captcha_rate': (self.stats['captcha_encounters'] / max(self.stats['total_searches'], 1)) * 100
        }
    
    def save_report(self, filename: str = None):
        if not filename:
            filename = f"performance_report_{datetime.now():%Y%m%d_%H%M%S}.json"
        
        report = {
            'statistics': self.stats,
            'summary': self.get_summary(),
            'search_times': self.search_times,
            'visit_times': self.visit_times
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"📊 گزارش عملکرد ذخیره شد: {filename}")
        except Exception as e:
            logger.error(f"❌ خطا در ذخیره گزارش عملکرد: {e}")

performance_monitor = PerformanceMonitor()
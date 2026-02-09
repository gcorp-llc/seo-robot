import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seo_admin.settings')
django.setup()

from bot_manager.models import SearchEngine, Device, SiteConfig, Keyword
from django.contrib.auth.models import User

def setup():
    # Create Superuser
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("Superuser created: admin / admin123")

    # Search Engines
    engines = [
        "Google", "Bing", "DuckDuckGo", "Yandex", "Yahoo", "Brave", "Ecosia", "Startpage"
    ]
    for name in engines:
        SearchEngine.objects.get_or_create(name=name)
    print("Search engines populated.")

    # Devices
    from config.general_settings import DEVICES
    for d in DEVICES:
        Device.objects.get_or_create(
            name=d['name'],
            defaults={'config_json': d}
        )
    print("Devices populated.")

    # Sample Site
    site, created = SiteConfig.objects.get_or_create(
        name="Dr Shakiba Vida",
        main_url="https://drshakibavida.com",
        articles_url="https://drshakibavida.com/%d9%85%d9%82%d8%a7%d9%84%d8%a7%d8%aa/",
        search_engines_enabled=True
    )
    if created:
        Keyword.objects.create(site=site, word="بهترین دکتر برای تزریق ژل در زعفرانیه")
        Keyword.objects.create(site=site, word="بهترین دکتر برای تزریق بوتاکس در زعفرانیه")
        print("Sample site created.")

if __name__ == "__main__":
    setup()

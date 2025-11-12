from config.proxy_config import proxy_manager

def select_best_proxy():
    return proxy_manager.get_best_proxy()
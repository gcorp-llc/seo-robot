from playwright.async_api import Route

async def intercept_route(route: Route) -> None:
    resource_type = route.request.resource_type
    if resource_type in ['image', 'media', 'font']:
        await route.abort()
    else:
        await route.continue_()
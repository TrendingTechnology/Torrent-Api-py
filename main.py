from typing import Optional
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
import uvicorn
from helper.is_site_available import check_if_site_available
import json
import os
import asyncio
import time
from dotenv import load_dotenv
import aioredis
from starlette.requests import Request
from starlette.responses import Response
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

load_dotenv()
app = FastAPI()


CACHE_EXPIRATION = int(os.getenv('CACHE_EXPIRATION', 180)) if os.getenv(
    'PYTHON_ENV', 'dev') == 'prod' else 30


@app.get("/api/v1/search")
@cache(expire=CACHE_EXPIRATION)
async def call_api(site: str, query: str, page: Optional[int] = 1):
    site = site.lower()
    all_sites = check_if_site_available(site)
    if all_sites:
        resp = await all_sites[site]['website']().search(query, page)
        if resp == None:
            return {"error": "website blocked change ip or domain"}
        elif len(resp['data']) > 0:
            return resp
        else:
            return {"error": "no results found"}
    return {"error": "invalid site"}


@app.get("/api/v1/trending")
@cache(expire=CACHE_EXPIRATION)
async def get_trending(site: str, category: Optional[str] = None, page: Optional[int] = 1):
    site = site.lower()
    all_sites = check_if_site_available(site)
    category = category.lower() if category else None
    if all_sites:
        if all_sites[site]['trending_available']:
            if category != None and not all_sites[site]["trending_category"]:
                return {"error": "search by trending category not available for {}".format(site)}
            if category != None and category not in all_sites[site]['categories']:
                return {"error": "selected category not available", "available_categories": all_sites[site]['categories']}
            resp = await all_sites[site]['website']().trending(category, page)
            if not resp:
                return {"error": "website blocked change ip or domain"}
            elif len(resp['data']) > 0:
                return resp
            else:
                return {"error": "no results found"}

        else:
            return {'error': "trending search not availabe for {}".format(site)}
    return {"error": "invalid site"}


@app.get("/api/v1/category")
@cache(expire=CACHE_EXPIRATION)
async def get_category(site: str, query: str, category: str, page: Optional[int] = 1):
    all_sites = check_if_site_available(site)
    site = site.lower()
    query = query.lower()
    category = category.lower()

    if all_sites:
        if all_sites[site]['search_by_category']:
            if category not in all_sites[site]['categories']:
                return {"error": "selected category not available", "available_categories": all_sites[site]['categories']}

            resp = await all_sites[site]['website']().search_by_category(query, category, page)
            if resp == None:
                return {"error": "website blocked change ip or domain"}
            elif len(resp['data']) > 0:
                return resp
            else:
                return {"error": "no results found"}
        else:
            return {"error": "search by category not available for {}".format(site)}
    return {"error": "invalid site"}


@app.get("/api/v1/recent")
@cache(expire=CACHE_EXPIRATION)
async def get_recent(site: str, category: Optional[str] = None, page: Optional[int] = 1):
    all_sites = check_if_site_available(site)
    site = site.lower()
    category = category.lower() if category else None

    if all_sites:
        if all_sites[site]['recent_available']:
            if category != None and not all_sites[site]["recent_category_available"]:
                return {"error": "search by recent category not available for {}".format(site)}
            if category != None and category not in all_sites[site]['categories']:
                return {"error": "selected category not available", "available_categories": all_sites[site]['categories']}
            resp = await all_sites[site]['website']().recent(category, page)
            if not resp:
                return {"error": "website blocked change ip or domain"}
            elif len(resp['data']) > 0:
                return resp
            else:
                return {"error": "no results found"}
        else:
            return {"error": "recent search not available for {}".format(site)}
    else:
        return {"error": "invalid site"}


@app.get("/api/v1/all/search")
@cache(expire=CACHE_EXPIRATION)
async def get_search_combo(query: str):
    start_time = time.time()
    # just getting all_sites dictionary
    all_sites = check_if_site_available('1337x')
    sites_list = list(all_sites.keys())
    tasks = []
    COMBO = {
        'data': []
    }
    total_torrents_overall = 0
    for site in sites_list:
        if all_sites[site]['website']:
            tasks.append(asyncio.create_task(
                all_sites[site]['website']().search(query, page=1)))
    results = await asyncio.gather(*tasks)
    for res in results:
        if res and len(res['data']) > 0:
            for torrent in res['data']:
                COMBO['data'].append(torrent)
            total_torrents_overall = total_torrents_overall + res['total']
    COMBO['time'] = time.time() - start_time
    COMBO['total'] = total_torrents_overall
    return COMBO


@app.get("/api/v1/all/trending")
@cache(expire=CACHE_EXPIRATION)
async def get_all_trending():
    start_time = time.time()
    # just getting all_sites dictionary
    all_sites = check_if_site_available('1337x')
    sites_list = [site for site in all_sites.keys(
    ) if all_sites[site]['trending_available'] and all_sites[site]['website']]
    tasks = []
    COMBO = {
        'data': []
    }
    total_torrents_overall = 0
    for site in sites_list:
        tasks.append(asyncio.create_task(
            all_sites[site]['website']().trending(category=None, page=1)))
    results = await asyncio.gather(*tasks)
    for res in results:
        if res and len(res['data']) > 0:
            for torrent in res['data']:
                COMBO['data'].append(torrent)
            total_torrents_overall = total_torrents_overall + res['total']
    COMBO['time'] = time.time() - start_time
    COMBO['total'] = total_torrents_overall
    return COMBO


@app.get("/api/v1/all/recent")
@cache(expire=CACHE_EXPIRATION)
async def get_all_recent():
    start_time = time.time()
    # just getting all_sites dictionary
    all_sites = check_if_site_available('1337x')
    sites_list = [site for site in all_sites.keys(
    ) if all_sites[site]['recent_available'] and all_sites[site]['website']]
    tasks = []
    COMBO = {
        'data': []
    }
    total_torrents_overall = 0
    for site in sites_list:
        tasks.append(asyncio.create_task(
            all_sites[site]['website']().recent(category=None, page=1)))
    results = await asyncio.gather(*tasks)
    for res in results:
        if res and len(res['data']) > 0:
            for torrent in res['data']:
                COMBO['data'].append(torrent)
            total_torrents_overall = total_torrents_overall + res['total']
    COMBO['time'] = time.time() - start_time
    COMBO['total'] = total_torrents_overall
    return COMBO


@app.get("/")
async def home():
    return FileResponse('README.md')


@app.on_event("startup")
async def startup():
    PYTHON_ENV = os.getenv('PYTHON_ENV', 'dev')
    if PYTHON_ENV == 'prod':
        HOST = os.getenv('REDIS_URI', 'redis://localhost')
    else:
        HOST = 'redis://localhost'
    redis = aioredis.from_url(
        HOST, encoding="utf8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=5000, log_level="info")

#!/usr/bin/env python3
"""hh_mcp — MCP-сервер для API hh.ru.

Каталог собран из официальной спеки api.hh.ru/openapi/specification/public:
133 метода, вакансии, отклики, резюме, справочники, статистика зарплат.

Авторизация: один токен приложения, заголовок `Authorization: Bearer <token>`.
Токен выдаётся в кабинете разработчика dev.hh.ru → Мои приложения.

Запуск:
    HH_TOKEN=... python -m hh_mcp.server
"""
from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from schema_mcp_core.client import MarketplaceClient, ServiceConfig
from schema_mcp_core.entities import EntityIndex
from schema_mcp_core.registry import Catalog
from schema_mcp_core.tools import register_cabinet_tools, register_generic_tools
from schema_mcp_core.transport import run as run_transport

CATALOG_PATH = Path(__file__).with_name("endpoints.yaml")


def _build_headers(creds: dict[str, str]) -> dict[str, str]:
    # hh требует и User-Agent с контактом приложения, иначе отвечает 400:
    # это его правило, а не общая практика.
    return {
        "Authorization": f"Bearer {creds.get('token', '')}",
        "HH-User-Agent": creds.get("app_name", "hh-mcp-ru (support@example.com)"),
    }


HH_CONFIG = ServiceConfig(
    name="hh",
    scheme="https",
    fields=["token", "app_name"],
    env_map={"token": "HH_TOKEN", "app_name": "HH_APP_NAME"},
    build_headers=_build_headers,
    allowed_host_suffixes=[".hh.ru"],
    whoami=("hh_get_me", ["first_name", "last_name", "email"]),
)


# Адрес документации API уходит в описание инструментов со свободным путём:
# каталог коннекторов Claude требует, чтобы такой инструмент называл свой API.
# Присваиваем после конструктора: поле появилось в schema-mcp-core позже,
# и на уже опубликованном ядре вызов с этим аргументом свалил бы импорт.
HH_CONFIG.api_docs = "https://api.hh.ru/openapi/specification/public"

mcp = FastMCP("hh-mcp-ru")
# Сущности сервиса лежат рядом с каталогом: у ядра своего файла нет и быть
# не может, разделы у ЭДО и у вакансий разные.
entities = EntityIndex.load(Path(__file__).with_name("entities.yaml"))
catalog = Catalog.from_yaml(CATALOG_PATH, entities=entities)
client = MarketplaceClient(HH_CONFIG)

register_generic_tools(
    mcp, svc="hh", client=client, catalog=catalog, entities=entities,
    key_help="dev.hh.ru → Мои приложения → создать приложение, взять access token. "
             "В HH_APP_NAME укажите имя приложения и контактный email: hh отклоняет "
             "запросы без внятного User-Agent.",
)
register_cabinet_tools(mcp, svc="hh", client=client, catalog=catalog)


def main() -> None:
    run_transport(mcp)


def cli() -> None:
    """Точка входа пакета: без аргументов сервер, с `doctor` диагностика."""
    import sys

    args = sys.argv[1:]
    if args and args[0] == "doctor":
        from schema_mcp_core.doctor import main as doctor_main

        raise SystemExit(doctor_main([("hh", "API hh.ru",
                                       "hh_mcp.server")], args[1:], "hh-mcp-ru"))
    if args:
        print(f"hh-mcp-ru: неизвестный аргумент {args[0]!r} (есть только 'doctor')",
              file=sys.stderr)
        raise SystemExit(2)
    main()


if __name__ == "__main__":
    main()

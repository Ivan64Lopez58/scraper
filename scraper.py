import asyncio
from typing import Dict, List
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import time

async def esperar_selector_optimizado(page, selector: str, max_wait=10) -> str:
    try:
        await page.wait_for_selector(selector, timeout=max_wait * 1000, state="visible")
        elemento = await page.query_selector(selector)
        if elemento:
            texto = (await elemento.inner_text()).strip()
            if texto:
                return texto
        raise Exception(f"Elemento {selector} sin texto")
    except Exception as e:
        raise TimeoutError(f"⏱ No se encontró {selector}: {str(e)}")

async def scrap_una_accion_optimizado(playwright, accion: Dict) -> Dict:
    browser = None
    try:
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-images',
                '--disable-javascript',
                '--disable-plugins',
                '--disable-extensions'
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1280, "height": 720},
            java_script_enabled=False,
            locale="en-US"
        )

        await context.route("**/*", lambda route, request: asyncio.create_task(
            route.abort() if request.resource_type in ["image", "media", "font", "stylesheet", "websocket", "eventsource"]
            else route.continue_()
        ))

        page = await context.new_page()
        print(f"🔍 Procesando {accion['empresa']}...")

        await page.goto(accion["url"], wait_until="domcontentloaded", timeout=30000)

        try:
            await page.click("button:has-text('Accept')", timeout=2000)
        except:
            try:
                await page.click("button:has-text('Aceptar')", timeout=1000)
            except:
                pass

        resultados = {}
        selectores = {
                'nombre_empresa': [
                "div.mb-1 h1",  # selector más directo
                "h1.text-xl.font-bold"  # alternativa
            ],
            'precio': [
                "[data-test='instrument-price-last']",
                ".text-2xl.font-bold",
                ".instrument-price_last__JQN7_"
            ],
            'cambio': [
                "[data-test='instrument-price-change']",
                ".text-sm.instrument-price_change__d9ElD"
            ],
            'cambio_pct': [
                "[data-test='instrument-price-change-percent']",
                ".text-sm"
            ],
            'moneda': [
                "[data-test='currency-in-label']",
                ".text-xs",
                "span.ml-1.5.font-bold"  # NUEVO selector adicional
            ],
            'pais': [
                "div.relative.flex.cursor-pointer.items-center span.flex-shrink",  # texto "Colombia"
                "div.relative.flex.cursor-pointer.items-center span.text-xs\\/5",  # mismo texto, más específico
            ],
            'hora_cierre': [
                "time[data-test='trading-time-label']"
            ],
            'estado_sesion': [  # Por si quieres mostrar "Open", "Closed", etc.
                "span[data-test='trading-state-label']"
            ]
}

  

        for campo, lista_selectores in selectores.items():
            valor = "N/A"
            for selector in lista_selectores:
                try:
                    valor = await esperar_selector_optimizado(page, selector, max_wait=5)
                    break
                except:
                    continue
            resultados[campo] = valor

        bolsa = "Desconocido"
        bolsa_selectores = [
            "div.flex.items-center.gap-1 span.text-xs\\/5.font-normal",
            ".text-xs.text-gray-500",
            "[data-test='exchange-name']"
        ]
        for selector in bolsa_selectores:
            try:
                elemento = await page.query_selector(selector)
                if elemento:
                    bolsa = (await elemento.inner_text()).strip()
                    break
            except:
                continue

        await browser.close()

        return {
            "nombre_empresa": resultados.get('nombre_empresa', accion["empresa"]),
            "empresa": accion["empresa"],
            "url": accion["url"],
            "precio": resultados.get('precio', 'N/A'),
            "cambio": resultados.get('cambio', 'N/A'),
            "cambio_pct": resultados.get('cambio_pct', 'N/A'),
            "moneda": resultados.get('moneda', 'N/A'),
            "pais": resultados.get('pais', 'N/A'),
            "estado_sesion": resultados.get('estado_sesion', 'N/A'),
            "hora_cierre": resultados.get('hora_cierre', 'N/A'),
            "bolsa": bolsa,
            "status": "✅ OK"
        }


    except Exception as e:
        if browser:
            await browser.close()
        print(f"❌ Error con {accion['empresa']}: {str(e)}")
        return {
            "empresa": accion["empresa"],
            "url": accion["url"],
            "precio": "Error",
            "cambio": "Error",
            "cambio_pct": "Error",
            "moneda": "Error",
            "bolsa": "Error",
            "status": f"❌ {str(e)[:50]}..."
        }

async def ejecutar_scraping_rapido(empresas: List[Dict]):
    print(f"🚀 Iniciando scraping de {len(empresas)} empresas (modo async)...")
    inicio = time.time()

    async with async_playwright() as p:
        tareas = [scrap_una_accion_optimizado(p, emp) for emp in empresas]
        resultados = await asyncio.gather(*tareas)

    tiempo_total = time.time() - inicio
    print(f"\n⏱ Tiempo total: {tiempo_total:.2f} segundos")
    print(f"⚡ Promedio por empresa: {tiempo_total / len(empresas):.2f} segundos")

    return resultados

if __name__ == "__main__":
    empresas = [
        {"empresa": "Apple", "url": "https://www.investing.com/equities/apple-drc"},
        {"empresa": "Microsoft", "url": "https://www.investing.com/equities/microsoft-corp"},
        {"empresa": "Google", "url": "https://www.investing.com/equities/google-inc-c"},
        {"empresa": "Tesla", "url": "https://www.investing.com/equities/tesla-motors"},
        {"empresa": "Amazon", "url": "https://www.investing.com/equities/amazon-com-inc"},
        {"empresa": "Apple", "url": "https://www.investing.com/equities/apple-drc"},
       ]

    resultados = asyncio.run(ejecutar_scraping_rapido(empresas))

    print("\n" + "="*80)
    print(" RESULTADOS FINALES:")
    print("="*80)
    for r in resultados:
        print(f"""
    {r.get('nombre_empresa', 'N/A')}
    {r['precio']} 
    {r['moneda']}
    {r['cambio']} 
    ({r['cambio_pct']})
    {r['bolsa']}
    {r.get('pais', 'N/A')}
    {r.get('estado_sesion', 'N/A')}
    {r.get('hora_cierre', 'N/A')}
    
    """)



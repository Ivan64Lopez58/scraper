import asyncio
import time
from typing import Dict, List
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from asyncio import Semaphore

SEM = Semaphore(10)  # Límite máximo de 10 navegadores activos

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
    context = None
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

        # Clic en botón de aceptar cookies si existe
        try:
            await page.click("button:has-text('Accept')", timeout=2000)
        except:
            try:
                await page.click("button:has-text('Aceptar')", timeout=1000)
            except:
                pass

        resultados = {}
        selectores = {
            'nombre_empresa': ["div.mb-1 h1", "h1.text-xl.font-bold"],
            'precio': ["[data-test='instrument-price-last']", ".text-2xl.font-bold", ".instrument-price_last__JQN7_"],
            'cambio': ["[data-test='instrument-price-change']", ".text-sm.instrument-price_change__d9ElD"],
            'cambio_pct': ["[data-test='instrument-price-change-percent']", ".text-sm"],
            'moneda': ["[data-test='currency-in-label']", ".text-xs", "span.ml-1.5.font-bold"],
            'pais': ["div.relative.flex.cursor-pointer.items-center span.flex-shrink", "div.relative.flex.cursor-pointer.items-center span.text-xs\\/5"],
            'hora_cierre': ["time[data-test='trading-time-label']"],
            'estado_sesion': ["span[data-test='trading-state-label']"],
            'logo_empresa': ["div.relative img.float-left"]

        }

        for campo, lista_selectores in selectores.items():
            valor = "N/A"
            for selector in lista_selectores:
                try:
                    await page.wait_for_selector(selector, timeout=5000, state="visible")
                    elemento = await page.query_selector(selector)
                    if elemento:
                        if campo == "logo_empresa":
                            src = await elemento.get_attribute("src")
                            if src:
                                valor = src.strip()
                                break
                        else:
                            texto = await elemento.inner_text()
                            if texto.strip():
                                valor = texto.strip()
                                break

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
            "logo_empresa": resultados.get('logo_empresa', 'N/A'),  # 👈 nuevo campo
            "bolsa": bolsa,
            "status": "✅ OK"
        }


    except Exception as e:
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

    finally:
        try:
            if context:
                await context.close()
                print(f"✅ Contexto cerrado para {accion['empresa']}")
        except Exception as e:
            print(f"⚠️ Error al cerrar context: {e}")

        try:
            if browser:
                await browser.close()
                print(f"✅ Navegador cerrado para {accion['empresa']}")
        except Exception as e:
            print(f"⚠️ Error al cerrar browser: {e}")

# ⛔ Esta función controla el límite de concurrencia
async def scrap_una_accion_con_semaforo(playwright, accion: Dict) -> Dict:
    async with SEM:
        return await scrap_una_accion_optimizado(playwright, accion)

async def ejecutar_scraping_rapido(empresas: List[Dict]):
    print(f"🚀 Iniciando scraping de {len(empresas)} empresas (máx 10 simultáneos)...")
    inicio = time.time()

    async with async_playwright() as p:
        tareas = [scrap_una_accion_con_semaforo(p, emp) for emp in empresas]
        resultados = await asyncio.gather(*tareas)

    tiempo_total = time.time() - inicio
    print(f"\n⏱ Tiempo total: {tiempo_total:.2f} segundos")
    print(f"⚡ Promedio por empresa: {tiempo_total / len(empresas):.2f} segundos")

    return resultados

if __name__ == "__main__":
    empresas = [
        {"empresa": "Boeing", "url": "https://www.investing.com/equities/boeing-co"}
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
        {r.get('logo_empresa', 'N/A')}
        """)


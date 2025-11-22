import asyncio
import json
import os
import random
from datetime import datetime
from urllib.parse import urlencode

from playwright.async_api import (
    Response,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from src.ai_handler import (
    download_all_images,
    get_ai_analysis,
    send_ntfy_notification,
    cleanup_task_images,
)
from src.config import (
    AI_DEBUG_MODE,
    API_URL_PATTERN,
    DETAIL_API_URL_PATTERN,
    LOGIN_IS_EDGE,
    RUN_HEADLESS,
    RUNNING_IN_DOCKER,
    STATE_FILE,
)
from src.parsers import (
    _parse_search_results_json,
    _parse_user_items_data,
    calculate_reputation_from_ratings,
    parse_ratings_data,
    parse_user_head_data,
)
from src.utils import (
    format_registration_days,
    get_link_unique_key,
    random_sleep,
    safe_get,
    save_to_jsonl,
    log_time,
)


async def scrape_user_profile(context, user_id: str) -> dict:
    """
    [Versão nova] Acessa o perfil do usuário especificado e coleta em sequência o resumo, a lista completa de produtos e a lista completa de avaliações.
    """
    print(f"   -> Iniciando a coleta completa das informações do usuário {user_id}...")
    profile_data = {}
    page = await context.new_page()

    # Preparar Futures e contêineres de dados para cada tarefa assíncrona
    head_api_future = asyncio.get_event_loop().create_future()

    all_items, all_ratings = [], []
    stop_item_scrolling, stop_rating_scrolling = asyncio.Event(), asyncio.Event()

    async def handle_response(response: Response):
        # Capturar a API de resumo do cabeçalho
        if "mtop.idle.web.user.page.head" in response.url and not head_api_future.done():
            try:
                head_api_future.set_result(await response.json())
                print(f"      [Captura de API] Informações do cabeçalho do usuário... sucesso")
            except Exception as e:
                if not head_api_future.done(): head_api_future.set_exception(e)

        # Capturar a API da lista de produtos
        elif "mtop.idle.web.xyh.item.list" in response.url:
            try:
                data = await response.json()
                all_items.extend(data.get('data', {}).get('cardList', []))
                print(f"      [Captura de API] Lista de produtos... {len(all_items)} itens coletados até agora")
                if not data.get('data', {}).get('nextPage', True):
                    stop_item_scrolling.set()
            except Exception as e:
                stop_item_scrolling.set()

        # Capturar a API da lista de avaliações
        elif "mtop.idle.web.trade.rate.list" in response.url:
            try:
                data = await response.json()
                all_ratings.extend(data.get('data', {}).get('cardList', []))
                print(f"      [Captura de API] Lista de avaliações... {len(all_ratings)} registros coletados até agora")
                if not data.get('data', {}).get('nextPage', True):
                    stop_rating_scrolling.set()
            except Exception as e:
                stop_rating_scrolling.set()

    page.on("response", handle_response)

    try:
        # --- Tarefa 1: navegar e coletar as informações do cabeçalho ---
        await page.goto(f"https://www.goofish.com/personal?userId={user_id}", wait_until="domcontentloaded", timeout=20000)
        head_data = await asyncio.wait_for(head_api_future, timeout=15)
        profile_data = await parse_user_head_data(head_data)

        # --- Tarefa 2: rolar para carregar todos os produtos (página padrão) ---
        print("      [Coleta] Iniciando a coleta da lista de produtos deste usuário...")
        await random_sleep(2, 4) # aguardar a conclusão da API da primeira página
        while not stop_item_scrolling.is_set():
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            try:
                await asyncio.wait_for(stop_item_scrolling.wait(), timeout=8)
            except asyncio.TimeoutError:
                print("      [Rolagem expirou] A lista de produtos provavelmente já foi carregada.")
                break
        profile_data["卖家发布的商品列表"] = await _parse_user_items_data(all_items)

        # --- Tarefa 3: clicar e coletar todas as avaliações ---
        print("      [Coleta] Iniciando a coleta da lista de avaliações deste usuário...")
        rating_tab_locator = page.locator("//div[text()='信用及评价']/ancestor::li")
        if await rating_tab_locator.count() > 0:
            await rating_tab_locator.click()
            await random_sleep(3, 5) # aguardar a conclusão da API da primeira página de avaliações

            while not stop_rating_scrolling.is_set():
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                try:
                    await asyncio.wait_for(stop_rating_scrolling.wait(), timeout=8)
                except asyncio.TimeoutError:
                    print("      [Rolagem expirou] A lista de avaliações provavelmente já foi carregada.")
                    break

            profile_data['卖家收到的评价列表'] = await parse_ratings_data(all_ratings)
            reputation_stats = await calculate_reputation_from_ratings(all_ratings)
            profile_data.update(reputation_stats)
        else:
            print("      [Aviso] Aba de avaliações não encontrada; coleta de avaliações ignorada.")

    except Exception as e:
        print(f"   [Erro] Falha ao coletar informações do usuário {user_id}: {e}")
    finally:
        page.remove_listener("response", handle_response)
        await page.close()
        print(f"   -> Coleta de informações do usuário {user_id} concluída.")

    return profile_data


async def scrape_xianyu(task_config: dict, debug_limit: int = 0):
    """
    [Executor principal]
    Com base na configuração de cada tarefa, coleta assincronamente dados de produtos do Goofish e executa análises de IA e notificações independentes em tempo real para cada novo item encontrado.
    """
    keyword = task_config['keyword']
    max_pages = task_config.get('max_pages', 1)
    personal_only = task_config.get('personal_only', False)
    min_price = task_config.get('min_price')
    max_price = task_config.get('max_price')
    ai_prompt_text = task_config.get('ai_prompt_text', '')

    processed_item_count = 0
    stop_scraping = False

    processed_links = set()
    output_filename = os.path.join("jsonl", f"{keyword.replace(' ', '_')}_full_data.jsonl")
    if os.path.exists(output_filename):
        print(f"LOG: Arquivo existente {output_filename} encontrado; carregando histórico para remover duplicatas...")
        try:
            with open(output_filename, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        link = record.get('商品信息', {}).get('商品链接', '')
                        if link:
                            processed_links.add(get_link_unique_key(link))
                    except json.JSONDecodeError:
                        print(f"   [Aviso] Uma linha do arquivo não pôde ser analisada como JSON e foi ignorada.")
            print(f"LOG: Carregamento concluído; {len(processed_links)} produtos já processados registrados.")
        except IOError as e:
            print(f"   [Aviso] Erro ao ler o arquivo de histórico: {e}")
    else:
        print(f"LOG: O arquivo de saída {output_filename} não existe; um novo arquivo será criado.")

    async with async_playwright() as p:
        if LOGIN_IS_EDGE:
            browser = await p.chromium.launch(headless=RUN_HEADLESS, channel="msedge")
        else:
            # Em ambiente Docker, usar o Chromium do Playwright; em ambiente local, usar o Chrome instalado no sistema
            if RUNNING_IN_DOCKER:
                browser = await p.chromium.launch(headless=RUN_HEADLESS)
            else:
                browser = await p.chromium.launch(headless=RUN_HEADLESS, channel="chrome")
        context = await browser.new_context(storage_state=STATE_FILE, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3")
        page = await context.new_page()

        try:
            log_time("Etapa 1 - navegando diretamente para a página de resultados de busca...")
            # Usar o parâmetro 'q' para montar a URL de busca correta, com codificação de URL
            params = {'q': keyword}
            search_url = f"https://www.goofish.com/search?{urlencode(params)}"
            log_time(f"URL de destino: {search_url}")

            # Usar expect_response para capturar os dados da API da busca inicial durante a navegação
            async with page.expect_response(lambda r: API_URL_PATTERN in r.url, timeout=30000) as response_info:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)

            initial_response = await response_info.value

            # Aguarda o carregamento dos elementos de filtro principais para confirmar a chegada à página de resultados
            await page.wait_for_selector('text=新发布', timeout=15000)

            # --- Novo: verificar se existe um pop-up de validação ---
            baxia_dialog = page.locator("div.baxia-dialog-mask")
            middleware_widget = page.locator("div.J_MIDDLEWARE_FRAME_WIDGET")
            try:
                # Aguardar até 2 segundos para o pop-up aparecer. Caso apareça, executar o bloco abaixo.
                await baxia_dialog.wait_for(state='visible', timeout=2000)
                print("\n==================== CRITICAL BLOCK DETECTED ====================")
                print("Foi detectado um pop-up anti-robô do Goofish (baxia-dialog); não é possível continuar.")
                print("Isso geralmente ocorre por excesso de requisições ou por identificação como robô.")
                print("Recomendações:")
                print("1. Interrompa o script por um tempo antes de tentar novamente.")
                print("2. (Recomendado) Defina RUN_HEADLESS=false no arquivo .env para executar em modo não headless, o que ajuda a evitar a detecção.")
                print(f"A tarefa '{keyword}' será interrompida aqui.")
                print("===================================================================")
                await browser.close()
                return processed_item_count
            except PlaywrightTimeoutError:
                # O pop-up não apareceu em 2 segundos, que é o comportamento esperado; continuar
                pass

            # Verificar se existe a camada de bloqueio J_MIDDLEWARE_FRAME_WIDGET
            try:
                await middleware_widget.wait_for(state='visible', timeout=2000)
                print("\n==================== CRITICAL BLOCK DETECTED ====================")
                print("Foi detectado um pop-up anti-robô do Goofish (J_MIDDLEWARE_FRAME_WIDGET); não é possível continuar.")
                print("Isso geralmente ocorre por excesso de requisições ou por identificação como robô.")
                print("Recomendações:")
                print("1. Interrompa o script por um tempo antes de tentar novamente.")
                print("2. (Recomendado) Atualize o arquivo de estado de login para garantir que o login ainda seja válido.")
                print("3. Reduza a frequência de execução das tarefas para evitar ser identificado como robô.")
                print(f"A tarefa '{keyword}' será interrompida aqui.")
                print("===================================================================")
                await browser.close()
                return processed_item_count
            except PlaywrightTimeoutError:
                # O pop-up não apareceu em 2 segundos, que é o comportamento esperado; continuar
                pass
            # --- Fim do bloco novo ---

            try:
                await page.click("div[class*='closeIconBg']", timeout=3000)
                print("LOG: Pop-up de anúncio fechado.")
            except PlaywrightTimeoutError:
                print("LOG: Nenhum pop-up de anúncio detectado.")

            final_response = None
            log_time("Etapa 2 - aplicando filtros...")
            await page.click('text=新发布')
            await random_sleep(2, 4) # antes: (1.5, 2.5)
            async with page.expect_response(lambda r: API_URL_PATTERN in r.url, timeout=20000) as response_info:
                await page.click('text=最新')
                # --- Ajuste: tempo de espera maior após aplicar a ordenação ---
                await random_sleep(4, 7) # antes: (3, 5)
            final_response = await response_info.value

            if personal_only:
                async with page.expect_response(lambda r: API_URL_PATTERN in r.url, timeout=20000) as response_info:
                    await page.click('text=个人闲置')
                    # --- Ajuste: substituir a espera fixa por espera aleatória mais longa ---
                    await random_sleep(4, 6) # antes era asyncio.sleep(5)
                final_response = await response_info.value

            if min_price or max_price:
                price_container = page.locator('div[class*="search-price-input-container"]').first
                if await price_container.is_visible():
                    if min_price:
                        await price_container.get_by_placeholder("¥").first.fill(min_price)
                        # --- Ajuste: substituir a espera fixa por espera aleatória ---
                        await random_sleep(1, 2.5) # antes era asyncio.sleep(5)
                    if max_price:
                        await price_container.get_by_placeholder("¥").nth(1).fill(max_price)
                        # --- Ajuste: substituir a espera fixa por espera aleatória ---
                        await random_sleep(1, 2.5) # antes era asyncio.sleep(5)

                    async with page.expect_response(lambda r: API_URL_PATTERN in r.url, timeout=20000) as response_info:
                        await page.keyboard.press('Tab')
                        # --- Ajuste: aumentar o tempo de espera após confirmar os preços ---
                        await random_sleep(4, 7) # antes era asyncio.sleep(5)
                    final_response = await response_info.value
                else:
                    print("LOG: Aviso - contêiner de preço não encontrado.")

            log_time("Todos os filtros foram aplicados; começando a processar a lista de produtos...")

            current_response = final_response if final_response and final_response.ok else initial_response
            for page_num in range(1, max_pages + 1):
                if stop_scraping: break
                log_time(f"Iniciando o processamento da página {page_num}/{max_pages} ...")

                if page_num > 1:
                    # Localizar o botão "Próxima página" não desativado. O Goofish usa a classe 'disabled' em vez do atributo disabled.
                    next_btn = page.locator("[class*='search-pagination-arrow-right']:not([class*='disabled'])")
                    if not await next_btn.count():
                        log_time("Última página alcançada; nenhum botão 'Próxima página' disponível. Parando a navegação.")
                        break
                    try:
                        async with page.expect_response(lambda r: API_URL_PATTERN in r.url, timeout=20000) as response_info:
                            await next_btn.click()
                            # --- Ajuste: aumentar o tempo de espera após mudar de página ---
                            await random_sleep(5, 8) # antes era (1.5, 3.5)
                        current_response = await response_info.value
                    except PlaywrightTimeoutError:
                        log_time(f"Tempo limite ao avançar para a página {page_num}; interrompendo a navegação.")
                        break

                if not (current_response and current_response.ok):
                    log_time(f"Resposta inválida na página {page_num}; ignorando.")
                    continue

                basic_items = await _parse_search_results_json(await current_response.json(), f"Página {page_num}")
                if not basic_items: break

                total_items_on_page = len(basic_items)
                for i, item_data in enumerate(basic_items, 1):
                    if debug_limit > 0 and processed_item_count >= debug_limit:
                        log_time(f"Limite de depuração atingido ({debug_limit}); parando a captura de novos produtos.")
                        stop_scraping = True
                        break

                    unique_key = get_link_unique_key(item_data["商品链接"])
                    if unique_key in processed_links:
                        log_time(f"[Progresso na página {i}/{total_items_on_page}] Produto '{item_data['商品标题'][:20]}...' já existe; ignorando.")
                        continue

                    log_time(f"[Progresso na página {i}/{total_items_on_page}] Novo produto encontrado; obtendo detalhes: {item_data['商品标题'][:30]}...")
                    # --- Ajuste: tempo de espera antes de abrir a página de detalhes, simulando um usuário lendo a lista ---
                    await random_sleep(3, 6) # 原来是 (2, 4)

                    detail_page = await context.new_page()
                    try:
                        async with detail_page.expect_response(lambda r: DETAIL_API_URL_PATTERN in r.url, timeout=25000) as detail_info:
                            await detail_page.goto(item_data["商品链接"], wait_until="domcontentloaded", timeout=25000)

                        detail_response = await detail_info.value
                        if detail_response.ok:
                            detail_json = await detail_response.json()

                            ret_string = str(await safe_get(detail_json, 'ret', default=[]))
                            if "FAIL_SYS_USER_VALIDATE" in ret_string:
                                print("\n==================== CRITICAL BLOCK DETECTED ====================")
                                print("检测到闲鱼反爬虫验证 (FAIL_SYS_USER_VALIDATE)，程序将终止。")
                                long_sleep_duration = random.randint(3, 60)
                                print(f"为避免账户风险，将执行一次长时间休眠 ({long_sleep_duration} 秒) 后再退出...")
                                await asyncio.sleep(long_sleep_duration)
                                print("长时间休眠结束，现在将安全退出。")
                                print("===================================================================")
                                stop_scraping = True
                                break

                            # 解析商品详情数据并更新 item_data
                            item_do = await safe_get(detail_json, 'data', 'itemDO', default={})
                            seller_do = await safe_get(detail_json, 'data', 'sellerDO', default={})

                            reg_days_raw = await safe_get(seller_do, 'userRegDay', default=0)
                            registration_duration_text = format_registration_days(reg_days_raw)

                            # --- START: 新增代码块 ---

                            # 1. 提取卖家的芝麻信用信息
                            zhima_credit_text = await safe_get(seller_do, 'zhimaLevelInfo', 'levelName')

                            # 2. 提取该商品的完整图片列表
                            image_infos = await safe_get(item_do, 'imageInfos', default=[])
                            if image_infos:
                                # 使用列表推导式获取所有有效的图片URL
                                all_image_urls = [img.get('url') for img in image_infos if img.get('url')]
                                if all_image_urls:
                                    # 用新的字段存储图片列表，替换掉旧的单个链接
                                    item_data['商品图片列表'] = all_image_urls
                                    # (可选) 仍然保留主图链接，以防万一
                                    item_data['商品主图链接'] = all_image_urls[0]

                            # --- END: 新增代码块 ---
                            item_data['“想要”人数'] = await safe_get(item_do, 'wantCnt', default=item_data.get('“想要”人数', 'NaN'))
                            item_data['浏览量'] = await safe_get(item_do, 'browseCnt', default='-')
                            # ...[此处可添加更多从详情页解析出的商品信息]...

                            # 调用核心函数采集卖家信息
                            user_profile_data = {}
                            user_id = await safe_get(seller_do, 'sellerId')
                            if user_id:
                                # 新的、高效的调用方式:
                                user_profile_data = await scrape_user_profile(context, str(user_id))
                            else:
                                print("   [警告] 未能从详情API中获取到卖家ID。")
                            user_profile_data['卖家芝麻信用'] = zhima_credit_text
                            user_profile_data['卖家注册时长'] = registration_duration_text

                            # 构建基础记录
                            final_record = {
                                "爬取时间": datetime.now().isoformat(),
                                "搜索关键字": keyword,
                                "任务名称": task_config.get('task_name', 'Untitled Task'),
                                "商品信息": item_data,
                                "卖家信息": user_profile_data
                            }

                            # --- START: Real-time AI Analysis & Notification ---
                            from src.config import SKIP_AI_ANALYSIS
                            
                            # 检查是否跳过AI分析并直接发送通知
                            if SKIP_AI_ANALYSIS:
                                log_time("环境变量 SKIP_AI_ANALYSIS 已设置，跳过AI分析并直接发送通知...")
                                # 下载图片
                                image_urls = item_data.get('商品图片列表', [])
                                downloaded_image_paths = await download_all_images(item_data['商品ID'], image_urls, task_config.get('task_name', 'default'))
                                
                                # 删除下载的图片文件，节省空间
                                for img_path in downloaded_image_paths:
                                    try:
                                        if os.path.exists(img_path):
                                            os.remove(img_path)
                                            print(f"   [图片] 已删除临时图片文件: {img_path}")
                                    except Exception as e:
                                        print(f"   [图片] 删除图片文件时出错: {e}")
                                
                                # 直接发送通知，将所有商品标记为推荐
                                log_time("商品已跳过AI分析，准备发送通知...")
                                await send_ntfy_notification(item_data, "商品已跳过AI分析，直接通知")
                            else:
                                log_time(f"开始对商品 #{item_data['商品ID']} 进行实时AI分析...")
                                # 1. Download images
                                image_urls = item_data.get('商品图片列表', [])
                                downloaded_image_paths = await download_all_images(item_data['商品ID'], image_urls, task_config.get('task_name', 'default'))

                                # 2. Get AI analysis
                                ai_analysis_result = None
                                if ai_prompt_text:
                                    try:
                                        # 注意：这里我们将整个记录传给AI，让它拥有最全的上下文
                                        ai_analysis_result = await get_ai_analysis(final_record, downloaded_image_paths, prompt_text=ai_prompt_text)
                                        if ai_analysis_result:
                                            final_record['ai_analysis'] = ai_analysis_result
                                            log_time(f"AI分析完成。推荐状态: {ai_analysis_result.get('is_recommended')}")
                                        else:
                                            final_record['ai_analysis'] = {'error': 'AI analysis returned None after retries.'}
                                    except Exception as e:
                                        print(f"   -> AI分析过程中发生严重错误: {e}")
                                        final_record['ai_analysis'] = {'error': str(e)}
                                else:
                                    print("   -> 任务未配置AI prompt，跳过分析。")

                                # 删除下载的图片文件，节省空间
                                for img_path in downloaded_image_paths:
                                    try:
                                        if os.path.exists(img_path):
                                            os.remove(img_path)
                                            print(f"   [图片] 已删除临时图片文件: {img_path}")
                                    except Exception as e:
                                        print(f"   [图片] 删除图片文件时出错: {e}")

                                # 3. Send notification if recommended
                                if ai_analysis_result and ai_analysis_result.get('is_recommended'):
                                    log_time("商品被AI推荐，准备发送通知...")
                                    await send_ntfy_notification(item_data, ai_analysis_result.get("reason", "无"))
                            # --- END: Real-time AI Analysis & Notification ---

                            # 4. 保存包含AI结果的完整记录
                            await save_to_jsonl(final_record, keyword)

                            processed_links.add(unique_key)
                            processed_item_count += 1
                            log_time(f"商品处理流程完毕。累计处理 {processed_item_count} 个新商品。")

                            # --- 修改: 增加单个商品处理后的主要延迟 ---
                            log_time("[反爬] 执行一次主要的随机延迟以模拟用户浏览间隔...")
                            await random_sleep(15, 30) # 原来是 (8, 15)，这是最重要的修改之一
                        else:
                            print(f"   错误: 获取商品详情API响应失败，状态码: {detail_response.status}")
                            if AI_DEBUG_MODE:
                                print(f"--- [DETAIL DEBUG] FAILED RESPONSE from {item_data['商品链接']} ---")
                                try:
                                    print(await detail_response.text())
                                except Exception as e:
                                    print(f"无法读取响应内容: {e}")
                                print("----------------------------------------------------")

                    except PlaywrightTimeoutError:
                        print(f"   错误: 访问商品详情页或等待API响应超时。")
                    except Exception as e:
                        print(f"   错误: 处理商品详情时发生未知错误: {e}")
                    finally:
                        await detail_page.close()
                        # --- 修改: 增加关闭页面后的短暂整理时间 ---
                        await random_sleep(2, 4) # 原来是 (1, 2.5)

                # --- 新增: 在处理完一页所有商品后，翻页前，增加一个更长的“休息”时间 ---
                if not stop_scraping and page_num < max_pages:
                    print(f"--- 第 {page_num} 页处理完毕，准备翻页。执行一次页面间的长时休息... ---")
                    await random_sleep(25, 50)

        except PlaywrightTimeoutError as e:
            print(f"\n操作超时错误: 页面元素或网络响应未在规定时间内出现。\n{e}")
        except Exception as e:
            print(f"\n爬取过程中发生未知错误: {e}")
        finally:
            log_time("任务执行完毕，浏览器将在5秒后自动关闭...")
            await asyncio.sleep(5)
            if debug_limit:
                input("按回车键关闭浏览器...")
            await browser.close()

    # 清理任务图片目录
    cleanup_task_images(task_config.get('task_name', 'default'))

    return processed_item_count

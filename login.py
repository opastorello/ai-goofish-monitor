import asyncio
import os
from PIL import Image
import qrcode
from playwright.async_api import async_playwright
import pyzbar.pyzbar as pyzbar

STATE_FILE = "xianyu_state.json"
LOGIN_IS_EDGE = os.getenv("LOGIN_IS_EDGE", "false").lower() == "true"
RUNNING_IN_DOCKER = os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true"


async def main():
    async with async_playwright() as p:
        print("Iniciando o navegador...")
        if LOGIN_IS_EDGE:
            browser = await p.chromium.launch(headless=False, channel="msedge")
        else:
            if RUNNING_IN_DOCKER:
                browser = await p.chromium.launch(headless=False)
            else:
                browser = await p.chromium.launch(headless=False, channel="chrome")

        context = await browser.new_context()
        page = await context.new_page()

        print("Abrindo a página inicial do Goofish...")
        await page.goto("https://www.goofish.com/")

        print("Aguardando o botão de login aparecer...")
        await page.wait_for_selector("div.nick--RyNYtDXM")
        await page.click("div.nick--RyNYtDXM")
        print("Botão de login clicado; aguardando o iframe...")

        try:
            frame_element = await page.wait_for_selector(
                "#alibaba-login-box", timeout=60000
            )
            frame = await frame_element.content_frame()
            print("Iframe de login carregado")
        except Exception as e:
            print(f"Falha ao carregar o iframe: {e}")
            return

        try:
            print("Aguardando o canvas do QR Code aparecer...")
            canvas_element = await frame.wait_for_selector(
                "#qrcode-img canvas", timeout=60000
            )
            print("Canvas do QR Code carregado; captura de tela salva como qrcode.png")
            await canvas_element.screenshot(path="qrcode.png")
        except Exception as e:
            print(f"Falha ao capturar o QR Code: {e}")
            return

        img = Image.open("qrcode.png")
        try:
            qr = pyzbar.decode(img)
            if qr:
                qr_data = qr[0].data.decode()
                print(f"Conteúdo do QR Code identificado: {qr_data}")
                qr_code = qrcode.QRCode(border=1)
                qr_code.add_data(qr_data)
                qr_code.make(fit=True)
                qr_code.print_ascii(invert=True)
            else:
                print("⚠️ Nenhum conteúdo do QR Code reconhecido; o QR Code foi salvo como qrcode.png")
        except ImportError:
            print("pyzbar não instalado; o QR Code foi salvo como qrcode.png")

        print("\n" + "=" * 50)
        print("Faça login manualmente na sua conta do Goofish na janela do navegador aberta.")
        print("Recomendamos usar o aplicativo para escanear o QR Code.")
        print("Depois de fazer login, volte aqui e pressione Enter para continuar...")
        print("=" * 50 + "\n")

        loop = asyncio.get_running_loop()
        # await loop.run_in_executor(None, input)

        print("Aguardando a conclusão do login...")

        try:
            print("Verificando se há solicitação de verificação via SMS...")
            sms_tip = None
            selectors = [
                "#J_Form > div > div.ui-tiptext.ui-tiptext-message",
                "div.ui-tiptext.ui-tiptext-message",
                ".ui-tiptext.ui-tiptext-message",
            ]
            for selector in selectors:
                try:
                    sms_tip = await frame.wait_for_selector(selector, timeout=30000)
                    if sms_tip:
                        break
                except:
                    continue

            if sms_tip:
                tip_text = await sms_tip.text_content()
                print(f"Texto de aviso detectado: {tip_text}")
                if "短信验证" in tip_text:
                    print("⚠️ Solicitação de código de verificação por SMS detectada")

                    get_code_button = await frame.wait_for_selector(
                        "#J_GetCode", timeout=10000
                    )
                    print("Clicando no botão para obter o código...")
                    await get_code_button.click()
                    print("Botão para obter o código clicado")

                    await frame.wait_for_selector("#J_Checkcode", timeout=10000)
                    print("Insira o código numérico de 6 dígitos recebido:")
                    verification_code = await loop.run_in_executor(None, input)

                    verification_input = await frame.wait_for_selector(
                        "#J_Checkcode", timeout=10000
                    )
                    await verification_input.fill(verification_code)
                    print(f"Código inserido: {verification_code}")

                    submit_button = await frame.wait_for_selector(
                        "#btn-submit", timeout=10000
                    )
                    await submit_button.click()
                    print("Botão de envio clicado")

                    try:
                        keep_button = await frame.wait_for_selector(
                            "button.fm-button.fm-submit.keep-login-btn.keep-login-confirm-btn.primary",
                            timeout=30000,
                        )
                        await keep_button.click()
                        print("✅ Botão 'Manter' detectado e clicado")
                    except Exception:
                        try:
                            await page.wait_for_selector(
                                "#alibaba-login-box", state="detached", timeout=30000
                            )
                            print("✅ Iframe desapareceu; login concluído")
                        except Exception:
                            print("⚠️ O login pode não ter sido concluído; verifique o estado da página")
            else:
                print("Nenhuma solicitação de verificação por SMS; continuando a verificar o status do login...")

                try:
                    keep_button = await frame.wait_for_selector(
                        "button.fm-button.fm-submit.keep-login-btn.keep-login-confirm-btn.primary",
                        timeout=30000,
                    )
                    await keep_button.click()
                    print("✅ Botão 'Manter' detectado e clicado")
                except Exception:
                    try:
                        await page.wait_for_selector(
                            "#alibaba-login-box", state="detached", timeout=30000
                        )
                        print("✅ Iframe desapareceu; login concluído")
                    except Exception:
                        print("⚠️ Status de login não confirmado; verifique a página manualmente")
        except Exception as e:
            print(f"Erro no fluxo de login: {e}")

        try:
            await context.storage_state(path=STATE_FILE)
            print(f"✅ Estado de login salvo em: {STATE_FILE}")
        except Exception as e:
            print(f"❌ Falha ao salvar o estado de login: {e}")

        # await browser.close()


if __name__ == "__main__":
    print("Iniciando o navegador para realizar o login...")
    asyncio.run(main())

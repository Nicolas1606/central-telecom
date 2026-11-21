"""Teste opcional de navegação. Inicie a demo com banco de teste antes de executar."""
import argparse
from playwright.sync_api import sync_playwright

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--url",default="http://127.0.0.1:8000")
    args=cli.parse_args()
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        page=browser.new_page()
        page.goto(args.url)
        page.locator("#question").fill("Minha fatura veio mais cara e se isso continuar quero cancelar")
        page.locator("#send").click()
        page.get_by_text("R$ 94,00",exact=False).first.wait_for()
        page.locator("summary").first.click()
        page.get_by_text("FAT-01 ·",exact=False).first.wait_for()
        page.locator("#question").fill("Quero cancelar agora")
        page.locator("#send").click()
        page.get_by_text("Protocolo ",exact=False).first.wait_for()
        page.get_by_role("button",name="Fila humana").click()
        page.get_by_role("button",name="Marcar como revisado").first.click()
        page.get_by_text("Revisado",exact=True).first.wait_for()
        page.get_by_role("button",name="Indicadores").click()
        page.get_by_text("Resolução confirmada").wait_for()
        browser.close()
        print("Chat, fontes, atendimento humano e painel OK.")
if __name__=="__main__":
    main()

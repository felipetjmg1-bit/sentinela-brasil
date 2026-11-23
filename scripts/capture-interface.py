from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"
OUT = Path("artifacts/interface")
OUT.mkdir(parents=True, exist_ok=True)
USERNAME = "ci-admin"
PASSWORD = "CI-Demo-Only-Password-2026!"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    desktop = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
    response = desktop.goto(BASE_URL, wait_until="networkidle", timeout=60000)
    assert response and response.status == 200
    desktop.get_by_role("heading", name="Sentinela Brasil").wait_for()
    desktop.get_by_label("Usuário").fill(USERNAME)
    desktop.get_by_label("Senha").fill(PASSWORD)
    desktop.get_by_role("button", name="Entrar").click()
    desktop.get_by_role("heading", name="Integridade do ledger").wait_for(timeout=30000)
    assert desktop.get_by_text("Demonstração local", exact=False).count() >= 1
    assert desktop.get_by_text("Sessão: ci-admin (admin)", exact=False).count() == 1
    desktop.screenshot(path=str(OUT / "sentinela-brasil-dashboard-desktop.png"), full_page=True)

    mobile = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
    mobile.goto(BASE_URL, wait_until="networkidle", timeout=60000)
    mobile.get_by_label("Usuário").fill(USERNAME)
    mobile.get_by_label("Senha").fill(PASSWORD)
    mobile.get_by_role("button", name="Entrar").click()
    mobile.get_by_role("heading", name="Integridade do ledger").wait_for(timeout=30000)
    mobile.screenshot(path=str(OUT / "sentinela-brasil-dashboard-mobile.png"), full_page=True)

    print("PASS: authenticated demo dashboard rendered; desktop/mobile screenshots saved.")
    browser.close()

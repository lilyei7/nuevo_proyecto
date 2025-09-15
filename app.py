#!/usr/bin/env python3
"""
Nuevo Proyecto - Clean Hotel Scraper
Solo con OTASync Integration y Intelligent Scraper
"""

from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def index():
    return """
    <h1>🏨 Nuevo Proyecto - Hotel Scraper</h1>
    <p>Proyecto limpio con:</p>
    <ul>
        <li>✅ OTASync Integration</li>
        <li>✅ Intelligent Scraper</li>
        <li>🚧 Interface nueva por construir</li>
    </ul>
    """

if __name__ == '__main__':
    print("🎉 Iniciando Nuevo Proyecto Hotel Scraper")
    print("📁 Componentes preservados:")
    print("   - otasync_integration.py")
    print("   - intelligent_scraper.py") 
    print("   - otasync_client.py")
    app.run(debug=True, port=5000)

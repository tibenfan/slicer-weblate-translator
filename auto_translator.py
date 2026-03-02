import os
import time
import requests
from typing import List
from dataclasses import dataclass

@dataclass
class TranslationUnit:
    id: int
    url: str
    source: str
    target: str
    state: int
    context: str

class WeblateAPI:
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Token {api_token}',
            'Content-Type': 'application/json'
        }
    
    def get_untranslated_units(self, project: str, component: str, language: str, limit: int) -> List[TranslationUnit]:
        url = f"{self.base_url}/api/translations/{project}/{component}/{language}/units/"
        params = {'q': 'state:empty', 'page_size': limit}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        units = []
        for result in data.get('results', []):
            unit = TranslationUnit(
                id=result['id'],
                url=result['url'],
                source=result['source'][0] if result['source'] else '',
                target=result['target'][0] if result['target'] else '',
                state=result['state'],
                context=result.get('context', '')
            )
            units.append(unit)
        return units
    
    def update_translation(self, unit_url: str, translated_text: str, state: int = 10) -> bool:
        payload = {'target': [translated_text], 'state': state}
        response = requests.patch(unit_url, headers=self.headers, json=payload)
        return response.status_code == 200

class DeepLTranslator:
    def __init__(self, api_key: str):
        self.api_key = api_key.strip()
        self.api_url = 'https://api-free.deepl.com/v2/translate'
        
    def translate(self, text: str) -> str:
        stripped_content = text.lstrip()
        leading_spaces = text[:len(text) - len(stripped_content)]
        
        if not stripped_content:
            return ""

        headers = {
            'Authorization': f'DeepL-Auth-Key {self.api_key}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        payload = {
            'text': stripped_content,
            'source_lang': 'EN',
            'target_lang': 'JA'
        }
        
        response = requests.post(self.api_url, headers=headers, data=payload)
        response.raise_for_status()
        
        translated_content = response.json()['translations'][0]['text']
        return leading_spaces + translated_content

def main():
    # GitHub Actions の環境変数から設定を読み込む
    WEBLATE_URL = os.getenv('WEBLATE_URL', 'https://hosted.weblate.org')
    WEBLATE_TOKEN = os.getenv('WEBLATE_TOKEN')
    PROJECT_NAME = os.getenv('PROJECT_NAME', '3d-slicer')
    COMPONENT_NAME = os.getenv('COMPONENT_NAME', 'slicerigt')
    DEEPL_API_KEY = os.getenv('TRANSLATOR_API_KEY')
    
    MAX_UNITS = int(os.getenv('MAX_UNITS', '50'))
    DELAY_SECONDS = float(os.getenv('DELAY_SECONDS', '1.0'))
    DRY_RUN = os.getenv('DRY_RUN', 'false').lower() == 'true'

    if not WEBLATE_TOKEN or not DEEPL_API_KEY:
        raise ValueError("APIトークンが設定されていません。")

    print(f"🚀 Weblate自動翻訳 (DeepL API版) を起動")
    print(f"プロジェクト: {PROJECT_NAME}/{COMPONENT_NAME}")
    print(f"最大処理件数: {MAX_UNITS}件")
    print(f"DRY RUN: {DRY_RUN}\n")
    
    try:
        weblate = WeblateAPI(WEBLATE_URL, WEBLATE_TOKEN)
        translator = DeepLTranslator(DEEPL_API_KEY)
        
        units = weblate.get_untranslated_units(PROJECT_NAME, COMPONENT_NAME, 'ja', MAX_UNITS)
        
        if not units:
            print("✅ 未翻訳の文字列はありませんでした")
            return
            
        print(f"📝 {len(units)}件の未翻訳文字列を処理します\n")
        
        success_count = 0
        for i, unit in enumerate(units, 1):
            print(f"--- [{i}/{len(units)}] ---")
            translated = translator.translate(unit.source)
            print(f"原文: {unit.source}")
            print(f"訳文: {translated}")
            
            if not DRY_RUN:
                if weblate.update_translation(unit.url, translated):
                    print("✅ アップロード成功")
                    success_count += 1
                else:
                    print("❌ アップロード失敗")
            else:
                print("🔷 DRY RUN: スキップ")
            
            time.sleep(DELAY_SECONDS)
            print("")
            
        print(f"🎉 処理完了！ ({success_count}/{len(units)} 件成功)")
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        exit(1) # GitHub Actions にエラーを伝える

if __name__ == '__main__':
    main()
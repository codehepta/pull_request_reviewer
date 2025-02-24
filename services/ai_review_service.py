import openai
import os
from dotenv import load_dotenv

load_dotenv()

class AIReviewService:
    def __init__(self, api_key=None, model="gpt-4"):  # Make model configurable
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('OPENAI_MODEL', model)  # Allow override via env var
        self.client = openai.OpenAI(api_key=self.api_key)
        
        self.language_prompts = {
            'en': "You are a helpful code review assistant. Provide a concise review of the following code diff, focusing on potential bugs, style issues, and best practices. Do not comment on the commit messages, just the code changes themselves.",
            'tr': "Sen yardımsever bir kod inceleme asistanısın. Aşağıdaki kod değişikliklerini, olası hataları, stil sorunlarını ve en iyi uygulamaları göz önünde bulundurarak özlü bir şekilde incele. Commit mesajları hakkında yorum yapma, sadece kod değişikliklerine odaklan.",
            'es': "Eres un asistente de revisión de código. Proporciona una revisión concisa del siguiente código, centrándote en posibles errores, problemas de estilo y mejores prácticas. No comentes los mensajes de commit, solo los cambios en el código.",
            'de': "Sie sind ein hilfreicher Code-Review-Assistent. Geben Sie eine präzise Überprüfung des folgenden Code-Diffs, konzentrieren Sie sich auf potenzielle Fehler, Stilfragen und Best Practices. Kommentieren Sie nicht die Commit-Nachrichten, sondern nur die Code-Änderungen selbst.",
            'fr': "Vous êtes un assistant de révision de code utile. Fournissez une revue concise du diff de code suivant, en vous concentrant sur les bugs potentiels, les problèmes de style et les meilleures pratiques. Ne commentez pas les messages de commit, uniquement les modifications du code."
        }

    def get_code_review(self, code_diff, language='en'):
        """Get code review in specified language"""
        try:
            system_prompt = self.language_prompts.get(language, self.language_prompts['en'])
            
            response = self.client.chat.completions.create(
                model=self.model,  # Use configured model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": code_diff}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error during AI review: {str(e)} (using model: {self.model})"
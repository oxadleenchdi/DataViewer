import locale
import streamlit as st
from locales.translations import en, zh

class I18n:
    def __init__(self):
        if "language" not in st.session_state:
            # Detect system language
            try:
                sys_lang = locale.getdefaultlocale()[0]
                if sys_lang and sys_lang.startswith('zh'):
                    st.session_state.language = "CH"
                else:
                    st.session_state.language = "EN"
            except:
                st.session_state.language = "EN"
        
        self.translations = {
            "EN": en,
            "CH": zh
        }

    def get(self, key, *args):
        lang = st.session_state.get("language", "EN")
        text = self.translations.get(lang, en).get(key, key)
        if args:
            return text.format(*args)
        return text

    def set_language(self, lang):
        st.session_state.language = lang

# Global instance
i18n = I18n()

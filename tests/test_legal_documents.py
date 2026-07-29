import unittest
from pathlib import Path


DOCUMENTS = Path(__file__).parents[1] / "app" / "assets" / "documents"


class LegalDocumentTests(unittest.TestCase):
    def read(self, name: str) -> str:
        return (DOCUMENTS / name).read_text(encoding="utf-8")

    def test_privacy_policy_contains_required_subjects(self) -> None:
        text = self.read("privacy.html")
        for subject in (
            "Оператор персональных данных",
            "Какие данные обрабатываются",
            "Цели и основания обработки",
            "Получатели и обработчики",
            "Трансграничная передача и локализация",
            "Сроки хранения",
            "Права пользователя",
        ):
            self.assertIn(subject, text)

    def test_terms_disclose_financial_conditions(self) -> None:
        text = self.read("terms.html")
        for condition in (
            "D + 1% комиссии сервиса",
            "При возврате покупатель получает D",
            "Telegram-каналы",
            "Неправильные и неопознанные платежи",
            "Споры",
            "Запрещённое использование",
        ):
            self.assertIn(condition, text)

    def test_service_description_matches_referral_economics(self) -> None:
        text = self.read("service.html")
        self.assertIn("10% комиссии сервиса", text)
        self.assertIn("0,1% от D", text)


if __name__ == "__main__":
    unittest.main()

from nicegui import ui
import os
from i18n import t, add_language_listener


SOFTWARE_NAME = "carla simpilot"
SOFTWARE_VERSION = "0.9.16"
SOFTWARE_LICENSE = "MIT License"
SOFTWARE_AUTHOR = "Ke Yingjie"
SOFTWARE_CONTACT = "yingjieke@gmail.com"


def build_about_tab():
    license_path = os.path.join(os.path.dirname(__file__), "LICENSE")
    try:
        with open(license_path, "r", encoding="utf-8") as f:
            license_text = f.read()
    except Exception:
        license_text = "无法加载 LICENSE 文件"

    license_dialog = ui.dialog()
    with license_dialog:
        with ui.card().classes("w-3/4 h-3/4"):
            license_title_label = ui.label("LICENSE").classes("text-lg font-medium")
            license_textarea = ui.textarea(value=license_text).props(
                "readonly"
            ).classes("w-full h-full")
            close_button = ui.button("关闭", on_click=license_dialog.close)

    def open_license_dialog():
        license_dialog.open()

    with ui.column().classes("w-full items-start gap-4"):
        with ui.card().classes("w-full"):
            app_name_label = ui.label(SOFTWARE_NAME).classes("text-xl font-bold")
            version_label = ui.label(f"版本：{SOFTWARE_VERSION}")
        with ui.card().classes("w-full"):
            features_title_label = ui.label(t("about.features_title")).classes(
                "text-lg font-medium"
            )
            feature1_label = ui.label(t("about.feature1"))
            feature2_label = ui.label(t("about.feature2"))
            feature3_label = ui.label(t("about.feature3"))
        with ui.card().classes("w-full"):
            license_title_label2 = ui.label(t("about.license_title")).classes(
                "text-lg font-medium"
            )
            with ui.row():
                license_name_label = ui.label(SOFTWARE_LICENSE)
                license_button = ui.button(
                    t("about.license_button"), on_click=open_license_dialog
                )
        with ui.card().classes("w-full"):
            author_title_label = ui.label(t("about.author_title")).classes(
                "text-lg font-medium"
            )
            author_label = ui.label(f"作者：{SOFTWARE_AUTHOR}")
            contact_label = ui.label(f"联系方式：{SOFTWARE_CONTACT}")

    def apply_language(lang):
        features_title_label.text = t("about.features_title")
        feature1_label.text = t("about.feature1")
        feature2_label.text = t("about.feature2")
        feature3_label.text = t("about.feature3")
        license_title_label2.text = t("about.license_title")
        license_button.text = t("about.license_button")
        author_title_label.text = t("about.author_title")

    add_language_listener(apply_language)

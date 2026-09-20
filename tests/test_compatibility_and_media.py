"""
Comprehensive Test Suite for Media Features & Multi-Language Text Compatibility
"""
import sys
import os
import shutil
import tempfile
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QUrl
import markdown2
import database
import media_manager
from styles import MARKDOWN_PREVIEW_CSS

def run_test(name, func):
    """Helper to run a test with standardized status logging."""
    print(f"RUNNING: {name} ...")
    try:
        func()
        print(f"[PASSED] {name}")
    except Exception as e:
        print(f"[FAILED] {name}: {e}")
        raise

# ============================================================================
# 1. Media Features Tests
# ============================================================================

def test_media_attachment_pipeline():
    """Verify attachments directory creation, copying, sanitization, and URL resolution."""
    att_dir = media_manager.get_attachments_dir()
    assert att_dir.exists(), "Attachments directory must exist"
    assert os.access(att_dir, os.W_OK), "Attachments directory must be writable"

    # Test with various file extensions and special characters in filename
    test_files = [
        ("mi foto vacación 2026.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"),
        ("grabación de voz (prueba #1).m4a", b"ftypM4A \x00\x00\x00\x00isomiso2"),
        ("video_test_presentation.mp4", b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00"),
        ("日本語の音声.wav", b"RIFF\x24\x00\x00\x00WAVEfmt ")
    ]

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        for orig_name, dummy_bytes in test_files:
            src_file = temp_path / orig_name
            src_file.write_bytes(dummy_bytes)

            copied = media_manager.copy_to_attachments(str(src_file))
            assert copied.exists(), f"Copied file must exist: {copied}"
            assert copied.stat().st_size == len(dummy_bytes), "File size must match original"

            # Check that filename was sanitized (no raw spaces or parenthesis)
            assert " " not in copied.name, "Copied filename must have spaces sanitized"
            
            # Check QUrl local file generation
            url = QUrl.fromLocalFile(str(copied)).toString()
            assert url.startswith("file:///"), f"URL must be valid file protocol: {url}"

            # Cleanup
            copied.unlink(missing_ok=True)

def test_voice_recorder_initialization():
    """Verify VoiceRecorder initializes without hardware exceptions."""
    recorder = media_manager.VoiceRecorder()
    assert recorder.session is not None
    assert recorder.recorder is not None
    assert recorder.audio_input is not None
    assert not recorder.is_recording()


# ============================================================================
# 2. Multi-Language & Text Input Compatibility Tests
# ============================================================================

INTERNATIONAL_TEST_CASES = [
    {
        "language": "Spanish (Español) - Accents & Inverted Punctuation",
        "title": "¡Notas Rápidas y Tareas para Mañana! 🇪🇸",
        "content": """# Plan del Día 📝
- ¿Cómo está el diseño del software?
- [x] Revisar la ortografía del niño
- [ ] Enviar el informe con *énfasis* en las **métricas clave**
- Ecuación: `á + é + í + ó + ú + ñ`"""
    },
    {
        "language": "French (Français) - Ligatures & Cedillas",
        "title": "Idées de Déjeuner & Français 🇫🇷",
        "content": """# Liste d'achats
- Un croissant chaud et du café crème
- Rendez-vous à 14h30 avec le maître d'hôtel
- **Attention:** Éléphant, cœur, forêt et garçon"""
    },
    {
        "language": "German (Deutsch) - Umlauts & Eszett",
        "title": "Projektübersicht & Aufgaben 🇩🇪",
        "content": """# Wichtige Mitteilung
- Größere Änderungen an der Schnittstelle
- Überprüfen Sie alle Wörterbücher und Äpfel
- **Wichtig:** `Schöne Grüße von der Baustelle`"""
    },
    {
        "language": "Arabic (العربية) - Right-to-Left (RTL) Script",
        "title": "ملاحظات هامة للاجتماع القادم 🇸🇦",
        "content": """# جدول الأعمال
- مراجعة التصميم الهندسي للتطبيق
- التأكد من دعم اللغة العربية بشكل كامل
- **ملاحظة:** الكتابة من اليمين إلى اليسار تعمل بسلاسة"""
    },
    {
        "language": "Hebrew (עברית) - Right-to-Left (RTL) Script",
        "title": "פתק חשוב לתכנון השבוע 🇮🇱",
        "content": """# רשימת משימות
- פגישת צוות ביום ראשון
- בדיקת תמיכה מלאה בכתיבה מימין לשמאל
- **הערה:** הכל עובד מצוין"""
    },
    {
        "language": "Simplified Chinese (简体中文) - CJK Characters",
        "title": "项目备忘录与功能清单 🇨🇳",
        "content": """# 今日工作总结
- [x] 完成便签界面的核心重构
- [ ] 测试跨语言输入法（拼音与五笔）
- **核心目标：** 简洁、快速、纯本地存储"""
    },
    {
        "language": "Japanese (日本語) - Kanji, Hiragana, Katakana",
        "title": "議事録とタスク管理 🇯🇵",
        "content": """# 本日のハイライト
- ユーザーインターフェースの改善完了
- [x] マークダウンエディタのテスト
- [ ] 音声メモ機能の動作検証
- **メモ:** カタカナとひらがなと漢字が正常に表示されます"""
    },
    {
        "language": "Korean (한국어) - Hangul Script",
        "title": "오늘의 업무 목록 및 아이디어 🇰🇷",
        "content": """# 개발 진행 상황
- [x] 파이썬 데스크톱 앱 빌드 완료
- [ ] 음성 녹음 기능 테스트
- **안내:** 한글 폰트와 자모 입력이 완벽하게 지원됩니다"""
    },
    {
        "language": "Emoji, Complex Graphemes & Math Symbols",
        "title": "Unicode 15.0 & Math Test 🚀🔥🎉",
        "content": """# Multi-byte Emojis & Math
- Software Engineer: 👩‍💻 👨‍💻
- Family: 👨‍👩‍👧‍👦
- Math Symbols: `∑(x_i) = ∫ f(x)dx`, `α + β ≤ γ`, `√144 = 12`, `π ≈ 3.14159`
- Currencies: `$100`, `€95.50`, `£82`, `¥14,000`, `₹7,500`"""
    },
    {
        "language": "Markdown Edge Cases & Inline HTML",
        "title": "Markdown Edge Cases & Tags",
        "content": """# Formatting Mix
- **Bold with *nested italic* and `inline code`**
- <u>Underlined text via standard HTML extension</u>
- ~~Strikethrough test~~
- [External Link](https://example.com)
- > Blockquote with *italics* and **bold**
| Column A | Column B |
| -------- | -------- |
| Value 1  | Value 2  |"""
    }
]

def test_multilanguage_database_roundtrip():
    """Verify that notes in all languages and scripts persist with 100% byte fidelity in SQLite."""
    database.init_db()
    created_ids = []

    for case in INTERNATIONAL_TEST_CASES:
        note_id = database.create_note(
            title=case["title"],
            content=case["content"],
            color_hex="#E1BEE7"
        )
        created_ids.append(note_id)

        # Retrieve and verify exact string equality
        retrieved = database.get_note(note_id)
        assert retrieved is not None, f"Note must exist for {case['language']}"
        assert retrieved["title"] == case["title"], f"Title mismatch in {case['language']}"
        assert retrieved["content"] == case["content"], f"Content mismatch in {case['language']}"

    # Clean up test notes
    database.delete_multiple_notes(created_ids)
    for note_id in created_ids:
        assert database.get_note(note_id) is None

def test_markdown_rendering_compatibility():
    """Verify that markdown2 renders international scripts, task lists, and HTML tags properly."""
    for case in INTERNATIONAL_TEST_CASES:
        html = markdown2.markdown(
            case["content"],
            extras=["fenced-code-blocks", "tables", "task_list", "strike"]
        )
        assert html is not None and len(html) > 0, f"HTML render failed for {case['language']}"
        
        # Verify specific tokens survive HTML rendering
        if "<u>" in case["content"]:
            assert "<u>" in html and "</u>" in html, "Underline HTML tags must be preserved"
        if "~~" in case["content"]:
            assert "<del>" in html or "<strike>" in html or "<s>" in html, "Strikethrough must convert to HTML"
        if "[x]" in case["content"]:
            assert "type=\"checkbox\"" in html or "checked" in html, "Task checkbox must render"

# ============================================================================
# Main Test Runner
# ============================================================================

def run_all():
    print("=" * 70)
    print("Sticky Notes: Media & International Input Compatibility Test Suite")
    print("=" * 70)

    run_test("Media Attachment Pipeline & Sanitization", test_media_attachment_pipeline)
    run_test("Voice Recorder Hardware Layer Initialization", test_voice_recorder_initialization)
    run_test("Multi-Language Database Roundtrip (UTF-8, RTL, CJK, Emojis)", test_multilanguage_database_roundtrip)
    run_test("Markdown2 International Script & HTML Rendering", test_markdown_rendering_compatibility)

    print("=" * 70)
    print("[ALL PASSED] All media, encoding, and language compatibility tests passed!")
    print("=" * 70)

if __name__ == "__main__":
    run_all()

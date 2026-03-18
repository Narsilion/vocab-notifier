from __future__ import annotations

import json
from html import escape
from pathlib import Path

from app.ack_server import acknowledgement_url
from app.config import Settings
from app.models import WordRecord
from app.presentation import primary_meaning, secondary_explanation


def write_word_page(output_dir: Path, word: WordRecord, settings: Settings) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    page_path = output_dir / f"{_slugify(word.display_term)}.html"
    page_path.write_text(_build_html(word, settings), encoding="utf-8")
    return page_path


def _build_html(word: WordRecord, settings: Settings) -> str:
    chips: list[str] = []
    if word.part_of_speech:
        chips.append(_chip(word.part_of_speech))
    if settings.render_translation and word.translation_text:
        chips.append(_chip(word.translation_text))
    if word.tags:
        chips.append(_chip(word.tags))

    explanation = secondary_explanation(word, settings)
    explanation_panel = ""
    if explanation:
        explanation_panel = f"""
        <article class="panel">
          <h2>Explanation</h2>
          <p>{escape(explanation)}</p>
        </article>
        """

    example_block = ""
    if _should_render_example(word):
        example_lines: list[str] = []
        if word.example_source:
            example_lines.append(
                f"""
        <div class="example-entry">
          <h3>Example sentence</h3>
          <p class="example-source">{escape(word.example_source)}</p>
        </div>
                """
            )
        if word.example_target:
            example_lines.append(
                f"""
        <div class="example-entry example-entry-translation">
          <h3>Example translation</h3>
          <p class="example-target">{escape(word.example_target)}</p>
        </div>
                """
            )
        example_block = f"""
      <section class="panel example-panel">
        <div class="panel-header">
          <h2>Example</h2>
          <button class="pronounce-button pronounce-button-inline" id="pronounce-example-button" type="button">
            Pronounce Example
          </button>
        </div>
        {''.join(example_lines)}
      </section>
        """

    meaning = escape(primary_meaning(word, settings))
    prefix = escape(word.display_prefix.upper()) if word.display_prefix else "TERM"
    display_term = escape(word.display_term)
    pronunciation_term = json.dumps(word.term)
    pronunciation_example = json.dumps(word.example_source or "")
    tts_language = json.dumps(settings.source_language_code)
    ack_url = json.dumps(acknowledgement_url(settings, card_id=word.id)) if word.id else "null"

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{display_term}</title>
    <style>
      :root {{
        --bg-top: #f2e8d7;
        --bg-bottom: #d8e5ec;
        --ink: #18222f;
        --muted: #52606f;
        --panel: rgba(255, 252, 246, 0.88);
        --accent: #bb5a34;
        --accent-soft: #e7b89f;
        --ring: rgba(24, 34, 47, 0.08);
        --shadow: 0 28px 80px rgba(24, 34, 47, 0.18);
      }}

      * {{
        box-sizing: border-box;
      }}

      body {{
        margin: 0;
        min-height: 100vh;
        font-family: "Avenir Next", "Helvetica Neue", sans-serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, rgba(255,255,255,0.78), transparent 32%),
          radial-gradient(circle at bottom right, rgba(187,90,52,0.16), transparent 28%),
          linear-gradient(160deg, var(--bg-top), var(--bg-bottom));
      }}

      .shell {{
        width: min(920px, calc(100vw - 32px));
        margin: 32px auto;
        padding: 28px;
        border: 1px solid var(--ring);
        border-radius: 28px;
        background: var(--panel);
        box-shadow: var(--shadow);
        backdrop-filter: blur(14px);
      }}

      .hero {{
        position: relative;
        overflow: hidden;
        padding: 28px;
        border-radius: 24px;
        background:
          linear-gradient(135deg, rgba(24,34,47,0.95), rgba(36,59,77,0.88)),
          linear-gradient(135deg, rgba(187,90,52,0.5), rgba(231,184,159,0.16));
        color: #f8f4ee;
      }}

      .hero::after {{
        content: "";
        position: absolute;
        inset: auto -8% -26% auto;
        width: 260px;
        height: 260px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(231,184,159,0.3), transparent 68%);
      }}

      .label {{
        display: inline-flex;
        align-items: center;
        padding: 6px 12px;
        border-radius: 999px;
        background: rgba(255,255,255,0.12);
        letter-spacing: 0.22em;
        font-size: 12px;
        text-transform: uppercase;
      }}

      h1 {{
        margin: 18px 0 6px;
        font-family: "Palatino", "Book Antiqua", serif;
        font-size: clamp(42px, 8vw, 72px);
        line-height: 0.95;
      }}

      .meaning {{
        margin: 0;
        font-size: clamp(20px, 3vw, 30px);
        color: rgba(248,244,238,0.84);
      }}

      .hero-actions {{
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 12px;
        margin-top: 18px;
      }}

      .pronounce-button {{
        appearance: none;
        border: 0;
        border-radius: 999px;
        padding: 12px 18px;
        font: inherit;
        font-weight: 600;
        color: #18222f;
        background: linear-gradient(135deg, #f8e7c6, #ffffff);
        box-shadow: 0 10px 24px rgba(24, 34, 47, 0.18);
        cursor: pointer;
      }}

      .pronounce-button:hover {{
        transform: translateY(-1px);
      }}

      .pronounce-button:disabled {{
        cursor: not-allowed;
        opacity: 0.65;
        transform: none;
      }}

      .pronounce-status {{
        min-height: 1.5em;
        font-size: 14px;
        color: rgba(248,244,238,0.84);
      }}

      .chips {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin: 22px 0 0;
      }}

      .chip {{
        padding: 8px 12px;
        border-radius: 999px;
        background: rgba(255,255,255,0.1);
        border: 1px solid rgba(255,255,255,0.14);
        font-size: 14px;
      }}

      .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 18px;
        margin-top: 18px;
      }}

      .panel {{
        padding: 22px;
        border-radius: 22px;
        background: rgba(255,255,255,0.72);
        border: 1px solid rgba(24,34,47,0.08);
      }}

      .panel h2 {{
        margin: 0 0 12px;
        font-size: 14px;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--muted);
      }}

      .panel-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        margin-bottom: 12px;
      }}

      .panel-header h2 {{
        margin: 0;
      }}

      .panel p {{
        margin: 0;
        font-size: 18px;
        line-height: 1.6;
      }}

      .example-panel {{
        margin-top: 18px;
        background:
          linear-gradient(135deg, rgba(255,255,255,0.88), rgba(231,184,159,0.26));
      }}

      .example-source {{
        font-family: "Palatino", "Book Antiqua", serif;
        font-size: 28px;
      }}

      .example-entry + .example-entry {{
        margin-top: 16px;
      }}

      .example-entry h3 {{
        margin: 0 0 6px;
        font-size: 13px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
      }}

      .example-target {{
        color: var(--muted);
      }}

      .pronounce-button-inline {{
        padding: 8px 14px;
        box-shadow: none;
        background: rgba(24, 34, 47, 0.08);
      }}

      .footer {{
        display: flex;
        justify-content: space-between;
        gap: 16px;
        margin-top: 18px;
        color: var(--muted);
        font-size: 14px;
      }}

      @media (max-width: 640px) {{
        .shell {{
          margin: 16px auto;
          padding: 16px;
        }}

        .hero {{
          padding: 22px;
        }}

        .footer {{
          flex-direction: column;
        }}

        .panel-header {{
          align-items: flex-start;
          flex-direction: column;
        }}
      }}
    </style>
  </head>
  <body>
    <main class="shell">
      <section class="hero">
        <span class="label">{prefix}</span>
        <h1>{display_term}</h1>
        <p class="meaning">{meaning}</p>
        <div class="hero-actions">
          <button class="pronounce-button" id="pronounce-button" type="button">Pronounce</button>
          <span class="pronounce-status" id="pronounce-status" aria-live="polite"></span>
        </div>
        <div class="chips">
          {''.join(chips)}
        </div>
      </section>

      <section class="grid">
        <article class="panel">
          <h2>Term</h2>
          <p>{display_term}</p>
        </article>
        <article class="panel">
          <h2>Card Meaning</h2>
          <p>{meaning}</p>
        </article>
        {explanation_panel}
      </section>

      {example_block}

      <div class="footer">
        <span>Generated by Vocab Notifier</span>
        <span id="page-status">Profile: {escape(settings.profile_name)}</span>
      </div>
    </main>
    <script>
      (() => {{
        const button = document.getElementById("pronounce-button");
        const exampleButton = document.getElementById("pronounce-example-button");
        const status = document.getElementById("pronounce-status");
        const pageStatus = document.getElementById("page-status");
        const wordText = {pronunciation_term};
        const exampleText = {pronunciation_example};
        const languageCode = {tts_language};
        const ackUrl = {ack_url};

        if (ackUrl) {{
          fetch(ackUrl, {{
            method: "GET",
            mode: "cors",
            cache: "no-store",
          }})
            .then((response) => {{
              if (response.ok && pageStatus) {{
                pageStatus.textContent = "Opened and marked as read";
              }}
            }})
            .catch(() => {{
              if (pageStatus) {{
                pageStatus.textContent = "Profile: {escape(settings.profile_name)}";
              }}
            }});
        }}

        if (!("speechSynthesis" in window) || typeof SpeechSynthesisUtterance === "undefined") {{
          button.disabled = true;
          if (exampleButton) {{
            exampleButton.disabled = true;
          }}
          status.textContent = "Pronunciation is not supported in this browser.";
          return;
        }}

        const speech = window.speechSynthesis;

        const chooseVoice = () => {{
          const voices = speech.getVoices();
          return voices.find((voice) => voice.lang === languageCode)
            || voices.find((voice) => voice.lang.toLowerCase().startsWith(languageCode.slice(0, 2).toLowerCase()))
            || null;
        }};

        const speak = (text, label) => {{
          if (!text) {{
            status.textContent = `${{label}} is unavailable.`;
            return;
          }}
          speech.cancel();
          const utterance = new SpeechSynthesisUtterance(text);
          utterance.lang = languageCode;
          utterance.rate = 0.9;

          const voice = chooseVoice();
          if (voice) {{
            utterance.voice = voice;
            status.textContent = `Voice: ${{voice.name}}`;
          }} else {{
            status.textContent = "Using browser default voice.";
          }}

          utterance.onend = () => {{
            status.textContent = "";
          }};
          utterance.onerror = () => {{
            status.textContent = "Pronunciation failed.";
          }};

          speech.speak(utterance);
        }};

        button.addEventListener("click", () => speak(wordText, "Term pronunciation"));
        if (exampleButton) {{
          exampleButton.addEventListener("click", () => speak(exampleText, "Example pronunciation"));
        }}

        if (typeof speech.onvoiceschanged !== "undefined") {{
          speech.onvoiceschanged = () => {{
            chooseVoice();
          }};
        }}
      }})();
    </script>
  </body>
</html>
"""


def _chip(value: str) -> str:
    return f"<span class=\"chip\">{escape(value)}</span>"


def _should_render_example(word: WordRecord) -> bool:
    if not (word.example_source or word.example_target):
        return False
    if _is_heuristic_example(word):
        return False
    return True


def _is_heuristic_example(word: WordRecord) -> bool:
    tags = (word.tags or "").lower()
    source = (word.source or "").lower()
    return "heuristic-enrichment" in tags or "heuristic-enrichment" in source


def _slugify(value: str) -> str:
    characters = []
    for char in value.lower():
        if char.isalnum():
            characters.append(char)
        elif char in {" ", "-", "_"}:
            characters.append("-")
    slug = "".join(characters).strip("-")
    return slug or "term"

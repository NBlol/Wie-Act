"""
Offline / degraded-mode generators.

Used when (a) no inference credentials are configured, or (b) both model
categories are unavailable after retries. Outputs are deterministic,
template- or retrieval-based, and ALWAYS labelled as such in the `ai`
metadata (`provider: "offline"`), so the UI can tell the learner exactly what
is happening instead of failing silently.  Nothing here pretends to be a
language model.
"""
from __future__ import annotations

import re
import typing as t

from app.utils import detect_language, truncate

NOTICE = {
    "en": "Offline demo mode: no AI inference key is configured, so this content was produced by EdNova's built-in rules (not by a language model).",
    "fr": "Mode démo hors ligne : aucune clé d'inférence IA n'est configurée ; ce contenu provient des règles intégrées d'EdNova (pas d'un modèle de langage).",
    "ar": "وضع العرض دون اتصال: لم يتم إعداد مفتاح للاستدلال بالذكاء الاصطناعي، لذا أُنتج هذا المحتوى بقواعد EdNova المدمجة (وليس بنموذج لغوي).",
    "tn": "وضع ديمو بلاش اتصال: ما فماش مفتاح AI مركّب، المحتوى هذا خرج من قواعد EdNova المدمجة (موش من موديل لغة).",
}

_T: dict[str, dict[str, str]] = {
    "hint_intro": {
        "en": "Let's work on **{topic}** together. Before the answer, here is a hint:",
        "fr": "Travaillons ensemble sur **{topic}**. Avant la réponse, voici un indice :",
        "ar": "لنعمل معاً على **{topic}**. قبل الجواب، إليك تلميحاً:",
        "tn": "يلا نخدمو مع بعضنا على **{topic}**. قبل الجواب، هاو تلميح:",
    },
    "direct_intro": {
        "en": "Here is what I found about **{topic}**:",
        "fr": "Voici ce que j'ai trouvé sur **{topic}** :",
        "ar": "هذا ما وجدته حول **{topic}**:",
        "tn": "هاو شنوّة لقيت على **{topic}**:",
    },
    "no_sources": {
        "en": "I don't have a knowledge model available right now. Try breaking the question into smaller parts, or upload a course document so I can search it for you.",
        "fr": "Je n'ai pas de modèle de connaissances disponible pour le moment. Essayez de découper la question en parties plus petites, ou téléversez un document de cours pour que je puisse y chercher.",
        "ar": "لا يتوفر لدي نموذج معرفي الآن. حاول تقسيم السؤال إلى أجزاء أصغر، أو ارفع وثيقة الدرس لأبحث فيها لك.",
        "tn": "توا ما عنديش موديل معرفة متاح. جرّب قسّم السؤال على أجزاء صغار، ولا حمّل وثيقة الدرس باش نلوّج فيها.",
    },
    "guiding_question": {
        "en": "In your own words, what is the first step you would take to approach this?",
        "fr": "Avec vos propres mots, quelle serait la première étape pour aborder cela ?",
        "ar": "بكلماتك أنت، ما هي الخطوة الأولى التي ستتخذها لمعالجة هذا؟",
        "tn": "بكلامك إنت، شنوّة أوّل خطوة باش تبدا بيها؟",
    },
    "next_step": {
        "en": "Next step: try a 3-question quiz on this topic, then come back with what felt unclear.",
        "fr": "Prochaine étape : faites un quiz de 3 questions sur ce sujet, puis revenez avec ce qui reste flou.",
        "ar": "الخطوة التالية: جرّب اختباراً من 3 أسئلة حول هذا الموضوع، ثم عد بما بقي غير واضح.",
        "tn": "الخطوة الجاية: جرّب كويز بـ 3 أسئلة على الموضوع هذا، وبعد أرجع بالّي ما فهمتوش.",
    },
    "style_tip": {
        "en": {
            "visual": "Sketch the idea as a diagram with boxes and arrows before reading the details.",
            "analogy": "Find an everyday situation that behaves the same way, then map each element.",
            "step_by_step": "Write the procedure as numbered steps and check each one before moving on.",
            "examples": "Start from two concrete examples and only then look for the general rule.",
            "repetition": "Say the key idea in two different ways, then test yourself after 10 minutes.",
            "problem_solving": "Pick one small exercise and try it before reading any theory.",
        },
        "fr": {
            "visual": "Dessinez l'idée sous forme de schéma avec des cases et des flèches avant de lire les détails.",
            "analogy": "Trouvez une situation du quotidien qui se comporte de la même façon, puis associez chaque élément.",
            "step_by_step": "Écrivez la procédure en étapes numérotées et vérifiez chacune avant de continuer.",
            "examples": "Partez de deux exemples concrets, puis seulement cherchez la règle générale.",
            "repetition": "Formulez l'idée clé de deux manières différentes, puis testez-vous après 10 minutes.",
            "problem_solving": "Choisissez un petit exercice et essayez-le avant de lire la théorie.",
        },
        "ar": {
            "visual": "ارسم الفكرة كمخطط بمربعات وأسهم قبل قراءة التفاصيل.",
            "analogy": "ابحث عن وضع يومي يتصرف بنفس الطريقة، ثم طابق كل عنصر.",
            "step_by_step": "اكتب الإجراء كخطوات مرقّمة وتحقق من كل خطوة قبل المتابعة.",
            "examples": "ابدأ بمثالين ملموسين ثم ابحث عن القاعدة العامة.",
            "repetition": "عبّر عن الفكرة الأساسية بطريقتين مختلفتين، ثم اختبر نفسك بعد 10 دقائق.",
            "problem_solving": "اختر تمريناً صغيراً وجرّبه قبل قراءة النظرية.",
        },
        "tn": {
            "visual": "ارسم الفكرة كيما سكيما بالمربعات والسهام قبل ما تقرا التفاصيل.",
            "analogy": "لوّج على حاجة من الحياة اليومية تتصرّف كيفها، وبعد طابق كل عنصر.",
            "step_by_step": "اكتب الطريقة خطوة خطوة بالأرقام وتثبّت في كل خطوة قبل ما تكمّل.",
            "examples": "ابدا بزوز أمثلة ملموسة وبعد لوّج على القاعدة العامة.",
            "repetition": "قول الفكرة الأساسية بزوز طرق مختلفة، وبعد جرّب روحك بعد 10 دقايق.",
            "problem_solving": "اختار تمرين صغير وجرّبو قبل ما تقرا النظرية.",
        },
    },
}


def _t(key: str, language: str, **kw: t.Any) -> str:
    table = _T[key]
    text = table.get(language, table["en"])
    return text.format(**kw) if kw else text


def _lang(inputs: dict) -> str:
    return inputs.get("language") or "en"


_SENT_SPLIT = re.compile(r"(?<=[.!?؟])\s+")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text or "") if len(s.strip()) > 20]


def _best_sentences(text: str, query: str, n: int = 2) -> list[str]:
    """Sentences of a passage that best overlap with the query (extractive QA, no model call)."""
    from app.rag.bm25 import tokenize

    sents = _sentences(text)
    if not sents:
        return [truncate(text, 240)] if text else []
    q = set(tokenize(query))
    if not q:
        return sents[:n]
    scored = [(len(q & set(tokenize(s))), -i, s) for i, s in enumerate(sents)]
    scored.sort(reverse=True)
    picked = [s for score, _, s in scored[:n] if score > 0] or sents[:n]
    return [s for s in sents if s in picked]


# ----------------------------------------------------------------------------- tasks

def tutor_triage(inputs: dict) -> dict:
    msg = inputs.get("message", "")
    low = msg.lower()
    confusion = "none"
    if re.search(r"(don'?t understand|confus|lost|still don'?t|comprends pas|compris|pas clair|ما فهمت|مش فاهم|فهمتش|مافهمتش|ما فهمتش|صعيب|difficile|hard)", low):
        confusion = "high" if re.search(r"(still|encore|again|توا زادة|مازلت|!{2,})", low) else "mild"
    intent = "explain"
    if re.search(r"(quiz|test me|exercises? for me|teste|اختبار|كويز|quizz)", low):
        intent = "quiz_request"
    elif re.search(r"(solve|answer|solution|result|réponse|solution|résultat|الحل|الجواب|النتيجة|احسب|calcule|compute|find x|=\s*\?)", low):
        intent = "answer_request"
    elif re.search(r"(exercise|exercice|problem|problème|homework|devoir|تمرين|مسألة|exo)", low):
        intent = "exercise_help"
    elif len(msg.split()) <= 3 and not re.search(r"\?|؟", msg):
        intent = "chit_chat" if re.search(r"(hi|hello|salut|bonjour|مرحبا|عسلامة|أهلا|hey|thanks|merci|شكرا|يعيشك)", low) else "other"
    complexity = "high" if (
        len(msg) > 220
        or re.search(r"(prove|proof|derive|why does|debug|optimi[sz]e|compare|analy[sz]e|démontr|pourquoi|برهن|لماذا|علاش|كيفاش نبرهن|```)", low)
    ) else "low"
    skip = {
        "comprends", "comment", "pourquoi", "aide", "aider", "expliquer", "explique", "exercice", "résoudre", "resoudre", "please", "explain",
        "understand", "help", "with", "this", "that", "what", "does", "could", "would", "about", "exercise", "solve", "question", "cette",
        "avec", "dans", "pour", "quoi", "don't", "dont", "doesn't", "can't", "cannot", "really", "still", "again", "encore", "toujours",
        "شنوة", "شنوّة", "كيفاش", "علاش", "فهمت", "فهمتش", "نحب", "ساعدني", "اشرح", "تمرين",
    }
    equation = re.search(r"[\w()]+\s*[+\-*/^=]\s*[\w()]+(?:\s*[+\-*/^=]\s*[\w()]+)*", msg)
    if equation and re.search(r"\d", equation.group(0)):
        topic = equation.group(0).strip()
    else:
        words = [w.strip("؟?!.,;:") for w in re.findall(r"[\w\u0600-\u06FF']{2,}", msg)]
        words = [w for w in words if w.lower() not in skip and len(w) >= 4]
        topic = " ".join(words[:5]) if words else "this topic"
    return {
        "language": detect_language(msg, inputs.get("preferred_language", "en")),
        "intent": intent,
        "confusion": confusion,
        "complexity": complexity,
        "topic": topic,
    }


def tutor_answer(inputs: dict) -> dict:
    language = _lang(inputs)
    style = inputs.get("learning_style") or "step_by_step"
    topic = inputs.get("topic") or truncate(inputs.get("message", ""), 40)
    sources: list[dict] = inputs.get("sources") or []
    mode = inputs.get("mode", "guided")
    hint_level = int(inputs.get("hint_level", 0))
    full = mode == "direct" or hint_level >= 2
    if inputs.get("conversational"):
        replies = {
            "en": "Of course — I’m here. Tell me what you’d like to talk about.",
            "fr": "Bien sûr — je suis là. Dis-moi de quoi tu aimerais parler.",
            "ar": "طبعاً، أنا هنا. أخبرني عمّا تريد أن نتحدث.",
            "tn": "أكيد، أنا موجود. احكيلي على شنوّة تحب نحكيو.",
        }
        return {"answer_md": replies.get(language, replies["en"]), "guiding_question": None, "next_step": None, "confusion_detected": "none"}
    if inputs.get("document_task") and sources:
        lines = {
            "en": ["## Document summary", ""],
            "fr": ["## Résumé du document", ""],
            "ar": ["## ملخص الوثيقة", ""],
            "tn": ["## ملخّص الوثيقة", ""],
        }.get(language, ["## Document summary", ""])
        for i, src in enumerate(sources, 1):
            sentences = _sentences(src.get("excerpt", ""))
            if sentences:
                lines.append(f"- {' '.join(sentences[:2])} [{i}]")
        return {"answer_md": "\n".join(lines).strip(), "guiding_question": None, "next_step": None, "confusion_detected": "none"}
    lines = [(_t("direct_intro", language, topic=topic) if full else _t("hint_intro", language, topic=topic)), ""]
    if sources:
        for i, src in enumerate(sources[: (4 if full else 2)], 1):
            sents = _best_sentences(src.get("excerpt", ""), inputs.get("message", ""), 3 if full else 1)
            if sents:
                lines.append(f"- {' '.join(sents)} [{i}]")
        lines.append("")
    else:
        lines.append(_t("no_sources", language))
        lines.append("")
    tip = _T["style_tip"].get(language, _T["style_tip"]["en"]).get(style, _T["style_tip"]["en"]["step_by_step"])
    lines.append(f"💡 {tip}")
    return {
        "answer_md": "\n".join(lines).strip(),
        "guiding_question": _t("guiding_question", language),
        "next_step": _t("next_step", language),
        "confusion_detected": inputs.get("confusion", "none"),
    }


def diagnostic_summary(inputs: dict) -> dict:
    language = _lang(inputs)
    style = inputs.get("learning_style") or "step_by_step"
    tips = _T["style_tip"].get(language, _T["style_tip"]["en"])
    explanation = {
        "en": f"Your answers suggest you learn best through the '{style.replace('_', ' ')}' approach (level: {inputs.get('level')}). EdNova will shape its explanations, hints and exercises accordingly.",
        "fr": f"Vos réponses suggèrent que vous apprenez mieux avec l'approche « {style.replace('_', ' ')} » (niveau : {inputs.get('level')}). EdNova adaptera ses explications, indices et exercices en conséquence.",
        "ar": f"تشير إجاباتك إلى أنك تتعلم بشكل أفضل عبر أسلوب '{style.replace('_', ' ')}' (المستوى: {inputs.get('level')}). سيكيّف EdNova شروحه وتلميحاته وتمارينه وفقاً لذلك.",
        "tn": f"إجاباتك تبيّن إلّي تتعلّم خير بطريقة '{style.replace('_', ' ')}' (المستوى: {inputs.get('level')}). EdNova باش يكيّف الشرح والتلميحات والتمارين على حسابك.",
    }
    recs = [tips.get(style, ""), tips.get(inputs.get("secondary_style") or "repetition", ""), _t("next_step", language)]
    return {"explanation": explanation.get(language, explanation["en"]), "recommendations": [r for r in recs if r]}


_STOP = set("the and for that this with from into your what which when where there their about have been were will would could should also than then them they these those very more most such only over under some".split())


def _keywords(text: str, n: int = 12) -> list[str]:
    words = re.findall(r"[A-Za-zÀ-ÿ؀-ۿ]{5,}", text)
    freq: dict[str, int] = {}
    for w in words:
        lw = w.lower()
        if lw in _STOP:
            continue
        freq[lw] = freq.get(lw, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:n]]


def quiz_generate(inputs: dict) -> dict:
    """Retrieval-based cloze questions when passages exist; labelled template questions otherwise."""
    language = _lang(inputs)
    n = int(inputs.get("num_questions", 5))
    sources: list[dict] = inputs.get("sources") or []
    questions: list[dict] = []
    text = " ".join(s.get("excerpt", "") for s in sources)
    keywords = _keywords(text, 40)
    labels = {
        "en": ("Fill in the blank:", "Which word completes the passage?", "Comprehension"),
        "fr": ("Complétez :", "Quel mot complète le passage ?", "Compréhension"),
        "ar": ("أكمل الفراغ:", "أي كلمة تكمل النص؟", "فهم"),
        "tn": ("كمّل الفراغ:", "شنوّة الكلمة إلّي تكمّل النص؟", "فهم"),
    }[language if language in ("en", "fr", "ar", "tn") else "en"]
    used: set[str] = set()
    for sent in _sentences(text):
        if len(questions) >= n:
            break
        candidates = [k for k in keywords if k in sent.lower() and k not in used]
        if not candidates:
            continue
        answer = candidates[0]
        used.add(answer)
        blanked = re.sub(re.escape(answer), "_____", sent, count=1, flags=re.I)
        distractors = [k for k in keywords if k != answer and k not in used][:3]
        if len(distractors) < 3:
            continue
        options = [answer, *distractors]
        # deterministic shuffle (stable across runs: sort by hash of word)
        options.sort(key=lambda w: hash(w) % 997)
        ids = ["a", "b", "c", "d"]
        questions.append(
            {
                "type": "mcq",
                "text": f"{labels[0]} {truncate(blanked, 260)}",
                "options": [{"id": ids[i], "text": o} for i, o in enumerate(options)],
                "correct_option_id": ids[options.index(answer)],
                "explanation": labels[1],
                "skill": labels[2],
            }
        )
    topic = inputs.get("topic") or "the topic"
    generic = {
        "en": [
            ("Which statement best describes the main idea of {t}?", ["It is the central concept of the lesson", "It is unrelated to the lesson", "It is only a historical note", "It is an unverified claim"], "a", "Main idea"),
            ("In your own words, give one everyday example of {t}.", None, None, "Transfer"),
            ("What is a common mistake learners make about {t}?", ["Confusing it with a related concept", "Spelling it wrong", "Ignoring the date", "None"], "a", "Misconceptions"),
            ("Which first step would you take to solve a problem about {t}?", ["Identify what is given and what is asked", "Guess the answer", "Skip to the conclusion", "Ask someone else"], "a", "Method"),
            ("Why is {t} useful?", None, None, "Purpose"),
        ],
        "fr": [
            ("Quelle affirmation décrit le mieux l'idée principale de {t} ?", ["C'est le concept central de la leçon", "Cela n'a pas de lien avec la leçon", "C'est seulement une note historique", "C'est une affirmation non vérifiée"], "a", "Idée principale"),
            ("Avec vos mots, donnez un exemple quotidien de {t}.", None, None, "Transfert"),
            ("Quelle erreur fréquente les apprenants font-ils sur {t} ?", ["Le confondre avec un concept proche", "Mal l'orthographier", "Ignorer la date", "Aucune"], "a", "Idées fausses"),
            ("Quelle première étape pour résoudre un problème sur {t} ?", ["Identifier les données et la question", "Deviner la réponse", "Sauter à la conclusion", "Demander à quelqu'un"], "a", "Méthode"),
            ("Pourquoi {t} est-il utile ?", None, None, "Finalité"),
        ],
        "ar": [
            ("أي عبارة تصف الفكرة الرئيسية لـ {t}؟", ["هو المفهوم المركزي للدرس", "لا علاقة له بالدرس", "هو مجرد ملاحظة تاريخية", "هو ادعاء غير مؤكد"], "a", "الفكرة الرئيسية"),
            ("بكلماتك، أعط مثالاً يومياً على {t}.", None, None, "النقل"),
            ("ما الخطأ الشائع الذي يقع فيه المتعلمون حول {t}؟", ["الخلط بينه وبين مفهوم قريب", "كتابته خطأ", "تجاهل التاريخ", "لا شيء"], "a", "المفاهيم الخاطئة"),
            ("ما أول خطوة لحل مسألة حول {t}؟", ["تحديد المعطيات والمطلوب", "تخمين الجواب", "الانتقال إلى الخلاصة", "سؤال شخص آخر"], "a", "الطريقة"),
            ("لماذا {t} مفيد؟", None, None, "الغاية"),
        ],
        "tn": [
            ("شنيّة الجملة إلّي توصف خير الفكرة الأساسية متاع {t}؟", ["هو المفهوم المركزي متاع الدرس", "ما عندو حتى علاقة بالدرس", "كان ملاحظة تاريخية", "كلام غير مؤكّد"], "a", "الفكرة الأساسية"),
            ("بكلامك، أعطي مثال من الحياة اليومية على {t}.", None, None, "التطبيق"),
            ("شنوّة الغلطة إلّي يعملوها برشا ناس على {t}؟", ["يخلطوه مع مفهوم قريب", "يكتبوه غالط", "ينسو التاريخ", "حتى شي"], "a", "الأغلاط الشائعة"),
            ("شنيّة أوّل خطوة باش تحلّ مسألة على {t}؟", ["نحدّد المعطيات والمطلوب", "نخمّن الجواب", "نقفز للنتيجة", "نسأل شكون آخر"], "a", "الطريقة"),
            ("علاش {t} مفيد؟", None, None, "الهدف"),
        ],
    }[language if language in ("en", "fr", "ar", "tn") else "en"]
    i = 0
    while len(questions) < n:
        text_q, options, correct, skill = generic[i % len(generic)]
        q: dict = {"text": text_q.format(t=topic), "skill": skill, "explanation": "Offline template question."}
        if options and "short" not in (inputs.get("question_types") or ["mcq"]) or options and i % 2 == 0:
            q.update({"type": "mcq", "options": [{"id": "abcd"[k], "text": o} for k, o in enumerate(options)], "correct_option_id": correct})
        else:
            q.update({"type": "short", "expected_answer": f"Any relevant, correct statement about {topic}."})
        questions.append(q)
        i += 1
    return {"questions": questions[:n]}


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[\w؀-ۿ]{3,}", (text or "").lower()) if w not in _STOP}


_GRADE_FEEDBACK = {
    1.0: {"en": "Good: your answer covers the key points.", "fr": "Bien : votre réponse couvre les points clés.", "ar": "جيد: إجابتك تغطي النقاط الأساسية.", "tn": "باهي: جوابك يغطّي النقاط الأساسية."},
    0.5: {"en": "Partially right: some key ideas are missing — compare with the expected answer.", "fr": "Partiellement juste : certaines idées clés manquent — comparez avec la réponse attendue.", "ar": "صحيح جزئياً: بعض الأفكار الأساسية ناقصة — قارن مع الإجابة المتوقعة.", "tn": "نصف نصف: فمة أفكار أساسية ناقصة — قارن مع الجواب المنتظر."},
    0.0: {"en": "Not yet: re-read the expected answer and try to restate it in your own words.", "fr": "Pas encore : relisez la réponse attendue et reformulez-la avec vos mots.", "ar": "ليس بعد: أعد قراءة الإجابة المتوقعة وحاول إعادة صياغتها بكلماتك.", "tn": "مازال: عاود اقرا الجواب المنتظر وجرّب قولو بكلامك."},
}


def grade_short_heuristic(expected_answer: str, learner_answer: str) -> float:
    """Token-overlap grader (used offline and as a sanity bound for model grades)."""
    expected = _tokens(expected_answer)
    given = _tokens(learner_answer)
    if not given:
        return 0.0
    overlap = len(expected & given) / max(1, len(expected))
    return 1.0 if overlap >= 0.6 else 0.5 if overlap >= 0.25 else 0.0


def quiz_grade_short(inputs: dict) -> dict:
    language = _lang(inputs)
    grades = []
    for item in inputs.get("items") or []:
        score = grade_short_heuristic(item.get("expected_answer", ""), item.get("learner_answer", ""))
        grades.append({"score": score, "feedback": _GRADE_FEEDBACK[score].get(language, _GRADE_FEEDBACK[score]["en"])})
    return {"grades": grades}


def quiz_feedback(inputs: dict) -> dict:
    language = _lang(inputs)
    results = inputs.get("results") or []
    weakest = next((r.get("skill") for r in results if not r.get("correct")), None)
    percent = inputs.get("percent", 0)
    style = inputs.get("learning_style") or "step_by_step"
    tip = _T["style_tip"].get(language, _T["style_tip"]["en"]).get(style, "")
    text = {
        "en": f"You scored {percent}%. " + (f"The skill to work on next is '{weakest}'. " if weakest else "Every skill is on track. ") + tip,
        "fr": f"Vous avez obtenu {percent} %. " + (f"La compétence à travailler : « {weakest} ». " if weakest else "Toutes les compétences sont en bonne voie. ") + tip,
        "ar": f"حصلت على {percent}%. " + (f"المهارة التي تحتاج إلى عمل: '{weakest}'. " if weakest else "كل المهارات على المسار الصحيح. ") + tip,
        "tn": f"جبت {percent}%. " + (f"المهارة إلّي تحب خدمة: '{weakest}'. " if weakest else "كل المهارات ماشية باهي. ") + tip,
    }
    return {"feedback": text.get(language, text["en"])}


def room_nudge(inputs: dict) -> dict:
    language = _lang(inputs)
    part = inputs.get("participation") or {}
    quiet = part.get("quiet_members") or []
    names = ", ".join(quiet[:3]) if quiet else None
    topic = inputs.get("topic", "")
    text = {
        "en": (f"Great energy so far! {names}, we'd love your take: what is one thing about {topic} that still feels unclear? Any question is welcome." if names else f"Nice discussion! Let's make sure everyone has a turn: who wants to summarise what we know about {topic} so far?"),
        "fr": (f"Belle énergie ! {names}, votre avis compte : qu'est-ce qui reste flou pour vous sur {topic} ? Toutes les questions sont bienvenues." if names else f"Belle discussion ! Vérifions que chacun a la parole : qui veut résumer ce que nous savons sur {topic} ?"),
        "ar": (f"حماس جميل! {names}، نود رأيكم: ما الشيء الذي لا يزال غير واضح حول {topic}؟ كل سؤال مرحب به." if names else f"نقاش رائع! لنتأكد أن للجميع دوراً: من يريد تلخيص ما نعرفه عن {topic}؟"),
        "tn": (f"برافو على النشاط! {names}، نحبّو نسمعو رأيكم: شنوّة الحاجة إلّي مازالت موش واضحة في {topic}؟ أي سؤال مرحبا بيه." if names else f"نقاش باهي! نتأكدو إلّي الكل عندو نوبة: شكون يحب يلخّص شنوّة نعرفو على {topic}؟"),
    }
    return {"message": text.get(language, text["en"])}


def room_guiding_question(inputs: dict) -> dict:
    language = _lang(inputs)
    topic = inputs.get("topic", "")
    text = {
        "en": f"Guiding question: if you had to explain {topic} to a friend in two sentences, what would you say — and which part would be hardest to justify?",
        "fr": f"Question guide : si vous deviez expliquer {topic} à un ami en deux phrases, que diriez-vous — et quelle partie serait la plus difficile à justifier ?",
        "ar": f"سؤال موجّه: لو كان عليك شرح {topic} لصديق في جملتين، ماذا ستقول — وأي جزء سيكون الأصعب تبريراً؟",
        "tn": f"سؤال موجّه: كان تحب تفسّر {topic} لصاحبك في زوز جمل، شنوّة تقول — وشنيّة الجزء الأصعب باش تبرّرو؟",
    }
    return {"message": text.get(language, text["en"])}


def room_check_explanation(inputs: dict) -> dict:
    language = _lang(inputs)
    text = {
        "en": "I can't verify this explanation automatically right now (no reasoning model available). Group checklist: 1) Is every term defined? 2) Does the explanation cover a concrete example? 3) Can someone find a counter-example? Compare with the course document before accepting it.",
        "fr": "Je ne peux pas vérifier cette explication automatiquement pour le moment (pas de modèle de raisonnement disponible). Check-list du groupe : 1) Chaque terme est-il défini ? 2) Y a-t-il un exemple concret ? 3) Quelqu'un trouve-t-il un contre-exemple ? Comparez avec le document de cours avant de l'accepter.",
        "ar": "لا أستطيع التحقق من هذا الشرح آلياً الآن (لا يتوفر نموذج استدلال). قائمة تحقق للمجموعة: 1) هل كل مصطلح معرّف؟ 2) هل هناك مثال ملموس؟ 3) هل يجد أحدكم مثالاً معاكساً؟ قارنوا مع وثيقة الدرس قبل قبوله.",
        "tn": "ما نجمش نتثبّت من الشرح هذا توا (ما فماش موديل استدلال). قائمة للمجموعة: 1) كل مصطلح مفسّر؟ 2) فمة مثال ملموس؟ 3) فمة شكون يلقى مثال معاكس؟ قارنوه بوثيقة الدرس قبل ما تقبلوه.",
    }
    return {"verdict": "unclear", "message": text.get(language, text["en"])}


def room_summary(inputs: dict) -> dict:
    language = _lang(inputs)
    msgs: list[dict] = inputs.get("messages") or []
    head = {"en": "## Session summary (extractive)", "fr": "## Résumé de la séance (extractif)", "ar": "## ملخص الجلسة (استخلاصي)", "tn": "## ملخّص الجلسة (استخلاصي)"}
    lines = [head.get(language, head["en"]), ""]
    by_author: dict[str, list[str]] = {}
    for m in msgs:
        by_author.setdefault(m.get("display_name", "?"), []).append(m.get("content", ""))
    for author, contents in by_author.items():
        lines.append(f"**{author}** ({len(contents)}): " + truncate(" / ".join(contents[-2:]), 220))
    lines.append("")
    lines.append(_t("next_step", language))
    return {"message": "\n".join(lines)}


def rag_answer(inputs: dict) -> dict:
    language = _lang(inputs)
    sources: list[dict] = inputs.get("sources") or []
    if not sources:
        return {"answer_md": _t("no_sources", language), "used_sources": []}
    intro = {"en": "Most relevant passages from your document:", "fr": "Passages les plus pertinents de votre document :", "ar": "أكثر المقاطع صلة في وثيقتك:", "tn": "أهمّ المقاطع إلّي عندها علاقة في وثيقتك:"}
    lines = [intro.get(language, intro["en"]), ""]
    used = []
    for i, src in enumerate(sources[:3], 1):
        sents = _best_sentences(src.get("excerpt", ""), inputs.get("question", ""), 2)
        lines.append(f"- {' '.join(sents)} [{i}]")
        used.append(i)
    return {"answer_md": "\n".join(lines), "used_sources": used}


def roadmap_generate(inputs: dict) -> dict:
    language = _lang(inputs)
    weeks = int(inputs.get("weeks", 4))
    goal = inputs.get("goal", "")
    style = inputs.get("learning_style") or "step_by_step"
    kinds_by_style = {
        "visual": ["watch", "read", "recall", "quiz"],
        "analogy": ["read", "discuss", "recall", "quiz"],
        "step_by_step": ["read", "practice", "practice", "quiz"],
        "examples": ["read", "practice", "discuss", "quiz"],
        "repetition": ["read", "recall", "recall", "quiz"],
        "problem_solving": ["practice", "practice", "discuss", "quiz"],
    }
    kinds = kinds_by_style.get(style, kinds_by_style["step_by_step"])
    labels = {
        "en": {"title": "Week {w}: {phase}", "phases": ["Foundations", "Core concepts", "Practice & connections", "Consolidation & mock test"], "obj": "Advance towards: {goal}", "acts": ["Read the key material and list 5 terms", "Work through 3 exercises", "Explain the concept to a peer in the room", "Take a 5-question quiz"], "cp": "Checkpoint: can you explain the week's idea in 2 sentences without notes?"},
        "fr": {"title": "Semaine {w} : {phase}", "phases": ["Fondations", "Concepts clés", "Pratique et liens", "Consolidation et examen blanc"], "obj": "Progresser vers : {goal}", "acts": ["Lire le matériel clé et lister 5 termes", "Faire 3 exercices", "Expliquer le concept à un pair dans la salle", "Faire un quiz de 5 questions"], "cp": "Point de contrôle : pouvez-vous expliquer l'idée de la semaine en 2 phrases sans notes ?"},
        "ar": {"title": "الأسبوع {w}: {phase}", "phases": ["الأسس", "المفاهيم الأساسية", "التطبيق والروابط", "التثبيت واختبار تجريبي"], "obj": "التقدم نحو: {goal}", "acts": ["اقرأ المادة الأساسية ودوّن 5 مصطلحات", "حلّ 3 تمارين", "اشرح المفهوم لزميل في الغرفة", "أجرِ اختباراً من 5 أسئلة"], "cp": "نقطة تحقق: هل تستطيع شرح فكرة الأسبوع في جملتين دون ملاحظات؟"},
        "tn": {"title": "الجمعة {w}: {phase}", "phases": ["الأساسيات", "المفاهيم الأساسية", "التطبيق والروابط", "التثبيت وامتحان تجريبي"], "obj": "نتقدّمو نحو: {goal}", "acts": ["اقرا المادة الأساسية واكتب 5 مصطلحات", "حلّ 3 تمارين", "فسّر المفهوم لصاحبك في الغرفة", "دير كويز بـ 5 أسئلة"], "cp": "نقطة تثبّت: تنجم تفسّر فكرة الجمعة في زوز جمل بلاش نوط؟"},
    }[language if language in ("en", "fr", "ar", "tn") else "en"]
    milestones = []
    for w in range(1, weeks + 1):
        phase = labels["phases"][min(w - 1, len(labels["phases"]) - 1)] if w <= 4 else labels["phases"][(w - 1) % 4]
        milestones.append(
            {
                "week": w,
                "title": labels["title"].format(w=w, phase=phase),
                "objective": labels["obj"].format(goal=goal),
                "activities": [{"text": labels["acts"][i], "kind": kinds[i]} for i in range(4)],
                "checkpoint": labels["cp"],
            }
        )
    return {"milestones": milestones}


def notes_generate(inputs: dict) -> dict:
    language = _lang(inputs)
    material = inputs.get("material", "")
    sents = _sentences(material)
    title = inputs.get("topic") or {"en": "Revision notes", "fr": "Notes de révision", "ar": "ملاحظات المراجعة", "tn": "نوط المراجعة"}.get(language, "Revision notes")
    head = {"en": "## Key points (extracted)", "fr": "## Points clés (extraits)", "ar": "## النقاط الأساسية (مستخلصة)", "tn": "## النقاط الأساسية (مستخلصة)"}
    lines = [f"# {title}", "", head.get(language, head["en"]), ""]
    for s in sents[:10]:
        lines.append(f"- {truncate(s, 220)}")
    flashcards = []
    if inputs.get("format", "both") in ("both", "flashcards"):
        for s in sents:
            m = re.match(r"^(.{3,60}?)\s+(is|are|means|refers to|est|sont|désigne|هو|هي|يعني)\s+(.{10,})$", s)
            if m:
                flashcards.append({"q": {"en": "What is", "fr": "Qu'est-ce que", "ar": "ما هو", "tn": "شنوّة"}.get(language, "What is") + f" {m.group(1)}?", "a": truncate(m.group(3), 200)})
            if len(flashcards) >= 8:
                break
    return {"title": title, "content_md": "\n".join(lines), "flashcards": flashcards}


OFFLINE_GENERATORS: dict[str, t.Callable[[dict], dict]] = {
    "tutor_triage": tutor_triage,
    "tutor_answer": tutor_answer,
    "diagnostic_summary": diagnostic_summary,
    "quiz_generate": quiz_generate,
    "quiz_grade_short": quiz_grade_short,
    "quiz_feedback": quiz_feedback,
    "room_nudge": room_nudge,
    "room_guiding_question": room_guiding_question,
    "room_check_explanation": room_check_explanation,
    "room_summary": room_summary,
    "rag_answer": rag_answer,
    "roadmap_generate": roadmap_generate,
    "notes_generate": notes_generate,
}

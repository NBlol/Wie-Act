"""
Learning-style & level diagnostic.

Six preference questions (each option maps to one of the six learning
styles) plus three short exercises of increasing difficulty. Scores are
computed deterministically in code; the compact model only writes the
human-readable summary. Interaction patterns (confusion events, quiz results)
refine the profile later.
"""
from __future__ import annotations

import typing as t

from app.utils import LEARNING_STYLES

_STYLE_ORDER = list(LEARNING_STYLES)

# option order is always: visual, analogy, step_by_step, examples, repetition, problem_solving
_PREFERENCE_QUESTIONS: dict[str, list[tuple[str, list[str]]]] = {
    "en": [
        ("When a concept is new to you, what helps most first?", ["A diagram or sketch of how the parts connect", "Comparing it to something I already know", "A numbered procedure I can follow", "Two or three concrete examples", "Hearing it explained twice in different words", "Trying a small problem right away"]),
        ("You have 10 minutes before an exam. You…", ["Redraw your mind-map", "Recall the analogies you used", "Re-read the steps of the method", "Go over worked examples", "Repeat the key definitions aloud", "Solve one last exercise"]),
        ("A friend explains something and you don't get it. You ask them to…", ["Draw it", "Compare it to everyday life", "Break it into steps", "Give an example", "Say it again more slowly", "Let you try it yourself"]),
        ("Which feedback is most useful after a mistake?", ["Showing where it sits in the overall picture", "An analogy that shows why it's wrong", "Pointing to the exact step that failed", "A similar example done correctly", "A recap of the rule", "Another exercise to retry immediately"]),
        ("Your ideal study group session…", ["Builds a shared diagram on the board", "Shares metaphors and stories", "Walks through a method together", "Collects real-life examples", "Quizzes each other on definitions", "Solves problems and compares answers"]),
        ("You remember things best when…", ["You can picture them", "They connect to something familiar", "You follow the logic step by step", "You have seen them in practice", "You have repeated them several times", "You have used them to solve something"]),
    ],
    "fr": [
        ("Quand un concept est nouveau, qu'est-ce qui vous aide le plus au départ ?", ["Un schéma de la façon dont les éléments se relient", "Le comparer à quelque chose que je connais", "Une procédure numérotée à suivre", "Deux ou trois exemples concrets", "L'entendre expliqué deux fois avec d'autres mots", "Essayer tout de suite un petit problème"]),
        ("Il vous reste 10 minutes avant un examen. Vous…", ["Redessinez votre carte mentale", "Repensez aux analogies utilisées", "Relisez les étapes de la méthode", "Revoyez des exemples corrigés", "Répétez les définitions clés à voix haute", "Résolvez un dernier exercice"]),
        ("Un ami explique quelque chose et vous ne comprenez pas. Vous lui demandez de…", ["Le dessiner", "Le comparer à la vie quotidienne", "Le découper en étapes", "Donner un exemple", "Le redire plus lentement", "Vous laisser essayer vous-même"]),
        ("Quel retour est le plus utile après une erreur ?", ["Montrer où elle se situe dans l'ensemble", "Une analogie qui montre pourquoi c'est faux", "Pointer l'étape exacte qui a échoué", "Un exemple similaire bien fait", "Un rappel de la règle", "Un autre exercice à refaire tout de suite"]),
        ("Votre séance de groupe idéale…", ["Construit un schéma commun au tableau", "Partage des métaphores et des histoires", "Déroule une méthode ensemble", "Rassemble des exemples réels", "S'interroge sur les définitions", "Résout des problèmes et compare les réponses"]),
        ("Vous retenez mieux quand…", ["Vous pouvez visualiser", "Cela se relie à quelque chose de familier", "Vous suivez la logique pas à pas", "Vous l'avez vu en pratique", "Vous l'avez répété plusieurs fois", "Vous l'avez utilisé pour résoudre quelque chose"]),
    ],
    "ar": [
        ("عندما يكون المفهوم جديداً عليك، ما الذي يساعدك أكثر في البداية؟", ["مخطط أو رسم يوضح كيف ترتبط الأجزاء", "مقارنته بشيء أعرفه مسبقاً", "إجراء مرقّم يمكنني اتباعه", "مثالان أو ثلاثة أمثلة ملموسة", "سماعه مشروحاً مرتين بكلمات مختلفة", "تجربة مسألة صغيرة فوراً"]),
        ("بقي لديك 10 دقائق قبل الامتحان. أنت…", ["تعيد رسم خريطتك الذهنية", "تستذكر التشبيهات التي استخدمتها", "تعيد قراءة خطوات الطريقة", "تراجع أمثلة محلولة", "تكرر التعريفات الأساسية بصوت عالٍ", "تحل تمريناً أخيراً"]),
        ("يشرح لك صديق شيئاً ولا تفهمه. تطلب منه أن…", ["يرسمه", "يقارنه بالحياة اليومية", "يقسمه إلى خطوات", "يعطي مثالاً", "يعيده بشكل أبطأ", "يتركك تجربه بنفسك"]),
        ("أي تغذية راجعة أكثر فائدة بعد الخطأ؟", ["إظهار موقعه في الصورة العامة", "تشبيه يوضح سبب الخطأ", "الإشارة إلى الخطوة التي فشلت بالضبط", "مثال مشابه محلول بشكل صحيح", "تذكير بالقاعدة", "تمرين آخر لإعادة المحاولة فوراً"]),
        ("جلسة المجموعة المثالية لك…", ["تبني مخططاً مشتركاً على اللوح", "تتبادل الاستعارات والقصص", "تمشي عبر طريقة معاً", "تجمع أمثلة من الواقع", "تختبر بعضها في التعريفات", "تحل مسائل وتقارن الإجابات"]),
        ("تتذكر الأشياء بشكل أفضل عندما…", ["تستطيع تصورها", "ترتبط بشيء مألوف", "تتبع المنطق خطوة خطوة", "رأيتها في التطبيق", "كررتها عدة مرات", "استخدمتها لحل شيء"]),
    ],
    "tn": [
        ("كي يكون المفهوم جديد عليك، شنوّة يعاونك أكثر في الأوّل؟", ["سكيما ولا رسمة تبيّن كيفاش الأجزاء مربوطين", "نقارنو بحاجة نعرفها", "طريقة بالأرقام نتبّعها خطوة خطوة", "زوز ولا ثلاثة أمثلة ملموسة", "نسمعو مفسّر مرتين بكلام مختلف", "نجرّب مسألة صغيرة ديراكت"]),
        ("بقالك 10 دقايق قبل الامتحان. إنت…", ["تعاود ترسم الخريطة الذهنية", "تتفكّر التشبيهات إلّي استعملتهم", "تعاود تقرا خطوات الطريقة", "تراجع أمثلة محلولة", "تعاود التعريفات الأساسية بصوت عالي", "تحلّ آخر تمرين"]),
        ("صاحبك يفسّرلك حاجة وما فهمتش. تطلب منّو…", ["يرسمها", "يقارنها بالحياة اليومية", "يقسمها خطوات", "يعطيك مثال", "يعاودها بالشوية", "يخلّيك تجرّب وحدك"]),
        ("شنوّة الفيدباك الأنفع بعد غلطة؟", ["يوريك وين موقعها في الصورة الكاملة", "تشبيه يبيّن علاش غالطة", "يشير للخطوة بالضبط إلّي غلطت فيها", "مثال مشابه محلول صحيح", "تذكير بالقاعدة", "تمرين آخر تعاودو ديراكت"]),
        ("حصّة المجموعة المثالية عندك…", ["نبنيو سكيما مشتركة على اللوحة", "نتبادلو تشبيهات وحكايات", "نمشيو في طريقة مع بعضنا", "نلمّو أمثلة من الواقع", "نسألو بعضنا على التعريفات", "نحلّو مسائل ونقارنو الأجوبة"]),
        ("تتفكّر الحاجات خير كي…", ["تنجم تتصوّرها", "تكون مربوطة بحاجة تعرفها", "تتبّع المنطق خطوة خطوة", "تكون شفتها في التطبيق", "عاودتها برشا مرّات", "استعملتها باش تحلّ حاجة"]),
    ],
}

# (question, options, correct_index, difficulty) – deliberately domain-neutral reasoning items
_EXERCISES: dict[str, list[tuple[str, list[str], int, str]]] = {
    "en": [
        ("A shirt costs 40 and is discounted by 25 %. What is the new price?", ["25", "30", "32", "35"], 1, "beginner"),
        ("Which number continues the sequence 2, 6, 18, 54, …?", ["108", "162", "216", "72"], 1, "intermediate"),
        ("If all Zorks are Blips and some Blips are Quins, which statement MUST be true?", ["All Zorks are Quins", "Some Quins are Zorks", "Every Zork is a Blip", "No Zork is a Quin"], 2, "advanced"),
    ],
    "fr": [
        ("Une chemise coûte 40 et bénéficie de 25 % de remise. Quel est le nouveau prix ?", ["25", "30", "32", "35"], 1, "beginner"),
        ("Quel nombre continue la suite 2, 6, 18, 54, … ?", ["108", "162", "216", "72"], 1, "intermediate"),
        ("Si tous les Zorks sont des Blips et certains Blips sont des Quins, quelle affirmation est NÉCESSAIREMENT vraie ?", ["Tous les Zorks sont des Quins", "Certains Quins sont des Zorks", "Chaque Zork est un Blip", "Aucun Zork n'est un Quin"], 2, "advanced"),
    ],
    "ar": [
        ("ثمن قميص 40 وعليه خصم 25%. ما هو السعر الجديد؟", ["25", "30", "32", "35"], 1, "beginner"),
        ("أي عدد يكمل المتتالية 2، 6، 18، 54، …؟", ["108", "162", "216", "72"], 1, "intermediate"),
        ("إذا كان كل زورك هو بليب وبعض البليب هم كوين، فأي عبارة صحيحة بالضرورة؟", ["كل الزورك هم كوين", "بعض الكوين هم زورك", "كل زورك هو بليب", "لا زورك هو كوين"], 2, "advanced"),
    ],
    "tn": [
        ("مريول سومو 40 وفيه تخفيض 25%. قدّاه السوم الجديد؟", ["25", "30", "32", "35"], 1, "beginner"),
        ("شنوّة العدد إلّي يكمّل السلسلة 2، 6، 18، 54، …؟", ["108", "162", "216", "72"], 1, "intermediate"),
        ("كان كل زورك هو بليب وبعض البليب هوما كوين، شنيّة الجملة إلّي أكيد صحيحة؟", ["الزورك الكل كوين", "بعض الكوين زورك", "كل زورك هو بليب", "حتى زورك موش كوين"], 2, "advanced"),
    ],
}

_OPTION_IDS = ["a", "b", "c", "d", "e", "f"]


def questions(language: str) -> list[dict]:
    language = language if language in _PREFERENCE_QUESTIONS else "en"
    out: list[dict] = []
    for i, (text, options) in enumerate(_PREFERENCE_QUESTIONS[language], 1):
        out.append(
            {
                "id": f"p{i}",
                "kind": "preference",
                "text": text,
                "options": [{"id": _OPTION_IDS[j], "text": opt, "style": _STYLE_ORDER[j]} for j, opt in enumerate(options)],
            }
        )
    for i, (text, options, correct, difficulty) in enumerate(_EXERCISES[language], 1):
        out.append(
            {
                "id": f"e{i}",
                "kind": "exercise",
                "text": text,
                "options": [{"id": _OPTION_IDS[j], "text": opt} for j, opt in enumerate(options)],
                "correct_option_id": _OPTION_IDS[correct],
                "difficulty": difficulty,
            }
        )
    return out


def score(answers: list[dict], self_reported_level: str | None) -> dict[str, t.Any]:
    style_scores = {s: 0 for s in _STYLE_ORDER}
    exercise_score = 0
    exercise_total = len(_EXERCISES["en"])
    exercises = {f"e{i}": _OPTION_IDS[correct] for i, (_, _, correct, _) in enumerate(_EXERCISES["en"], 1)}
    for ans in answers:
        qid, oid = ans.get("question_id", ""), ans.get("option_id", "")
        if qid.startswith("p") and oid in _OPTION_IDS[:6]:
            style_scores[_STYLE_ORDER[_OPTION_IDS.index(oid)]] += 1
        elif qid in exercises and exercises[qid] == oid:
            exercise_score += 1
    ranked = sorted(style_scores.items(), key=lambda kv: (-kv[1], _STYLE_ORDER.index(kv[0])))
    primary = ranked[0][0] if ranked[0][1] > 0 else "step_by_step"
    secondary = ranked[1][0] if len(ranked) > 1 and ranked[1][1] > 0 else None
    # level: exercise performance, nudged by self-report
    level = "beginner" if exercise_score <= 1 else "intermediate" if exercise_score == 2 else "advanced"
    if self_reported_level in ("beginner", "intermediate", "advanced"):
        order = ["beginner", "intermediate", "advanced"]
        # average the two signals, rounding towards the measured one
        measured, reported = order.index(level), order.index(self_reported_level)
        level = order[round((2 * measured + reported) / 3)]
    return {
        "learning_style": primary,
        "secondary_style": secondary,
        "level": level,
        "style_scores": style_scores,
        "exercise_score": exercise_score,
        "exercise_total": exercise_total,
    }

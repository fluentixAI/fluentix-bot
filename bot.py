from __future__ import annotations

import os
import random
from datetime import date
from typing import Dict, Set

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# =========================
# CONFIG (Render-ready)
# =========================
TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not TOKEN:
    raise ValueError("BOT_TOKEN is not set. Add it in Render (Environment Variables).")

FREE_LIMIT_PER_DAY = 5  # FREE users: starts per day

# =========================
# IN-MEMORY STORAGE
# (later we can replace with SQLite)
# =========================
user_lang: Dict[int, str] = {}             # user_id -> "en"/"ru"/"tj"
user_plan: Dict[int, str] = {}             # user_id -> "free"/"premium"
user_level: Dict[int, str] = {}            # user_id -> "A1".."C2"
free_usage: Dict[int, Dict[str, int]] = {} # user_id -> {"day": "...", "count": int}

# writing mode
user_mode: Dict[int, str] = {}             # user_id -> "writing_waiting" or ""
user_last_prompt: Dict[int, str] = {}      # user_id -> last prompt

# referral
ref_invited_users: Dict[int, Set[int]] = {}  # referrer_id -> set(invited_user_ids)
ref_count: Dict[int, int] = {}               # referrer_id -> count

# =========================
# TEXTS (FULL LOCALIZED)
# =========================
TXT = {
    "start_choose_lang": {
        "en": "👋 Welcome to Fluentix AI!\n\nPlease choose your language:",
        "ru": "👋 Добро пожаловать в Fluentix AI!\n\nПожалуйста, выберите язык:",
        "tj": "👋 Хуш омадед ба Fluentix AI!\n\nЛутфан забони худро интихоб кунед:",
    },
    "plan_title": {
        "en": "💎 Choose your plan",
        "ru": "💎 Выберите тариф",
        "tj": "💎 Тарҳро интихоб кунед",
    },
    "plan_desc": {
        "en": (
            "🌱 FREE:\n"
            f"• Up to {FREE_LIMIT_PER_DAY} starts per day\n"
            "• Basic feedback\n\n"
            "💎 PREMIUM:\n"
            "• Unlimited access\n"
            "• Best feedback\n\n"
            "Choose one option below:"
        ),
        "ru": (
            "🌱 FREE:\n"
            f"• До {FREE_LIMIT_PER_DAY} запусков в день\n"
            "• Базовый feedback\n\n"
            "💎 PREMIUM:\n"
            "• Безлимит\n"
            "• Лучший feedback\n\n"
            "Выберите вариант ниже:"
        ),
        "tj": (
            "🌱 FREE:\n"
            f"• То {FREE_LIMIT_PER_DAY} маротиба дар як рӯз\n"
            "• Feedback-и оддӣ\n\n"
            "💎 PREMIUM:\n"
            "• Бе маҳдудият\n"
            "• Feedback-и беҳтарин\n\n"
            "Яке аз вариантҳоро интихоб кунед:"
        ),
    },
    "premium_pay_info": {
        "en": "💳 Premium ($1.99) selected.\n\nPayment will be added soon. For now, use Invite method 🎁.",
        "ru": "💳 Premium ($1.99) выбран.\n\nОплату добавим скоро. Пока используйте приглашения 🎁.",
        "tj": "💳 Premium ($1.99) интихоб шуд.\n\nПардохт ба зудӣ илова мешавад. Ҳоло роҳи даъват 🎁-ро истифода баред.",
    },
    "invite_info": {
        "en": (
            "🎁 Get PREMIUM for FREE!\n\n"
            "Invite 2 friends with your personal link.\n"
            "When 2 friends start the bot via your link, Premium activates automatically.\n\n"
            "Your link:"
        ),
        "ru": (
            "🎁 Получите PREMIUM бесплатно!\n\n"
            "Пригласите 2 друзей по вашей ссылке.\n"
            "Когда 2 друга запустят бота по вашей ссылке — Premium включится автоматически.\n\n"
            "Ваша ссылка:"
        ),
        "tj": (
            "🎁 PREMIUM-ро ройгон гиред!\n\n"
            "2 дӯстро бо линкатон даъват кунед.\n"
            "Вақте 2 нафар бо линкатон ботро start кунанд — Premium автоматӣ фаъол мешавад.\n\n"
            "Линки шумо:"
        ),
    },
    "invite_progress": {
        "en": "📈 Progress: {count}/2 invited.",
        "ru": "📈 Прогресс: {count}/2 приглашено.",
        "tj": "📈 Пешравӣ: {count}/2 даъват шуд.",
    },
    "invite_success_notify": {
        "en": "🎉 Congrats! You invited 2 friends and unlocked PREMIUM ✅",
        "ru": "🎉 Поздравляем! Вы пригласили 2 друзей и получили PREMIUM ✅",
        "tj": "🎉 Табрик! Шумо 2 дӯстро даъват кардед ва PREMIUM гирифтед ✅",
    },
    "choose_level_title": {
        "en": "📊 Select your English level:",
        "ru": "📊 Выберите уровень английского:",
        "tj": "📊 Сатҳи англисии худро интихоб кунед:",
    },
    "level_saved": {
        "en": "✅ Level saved: {lvl}\n\nNow choose a section:",
        "ru": "✅ Уровень выбран: {lvl}\n\nТеперь выберите раздел:",
        "tj": "✅ Сатҳ интихоб шуд: {lvl}\n\nҲоло қисмро интихоб кунед:",
    },
    "skills_title": {
        "en": "🎯 Choose a section:",
        "ru": "🎯 Выберите раздел:",
        "tj": "🎯 Қисмро интихоб кунед:",
    },
    "free_limit_reached": {
        "en": f"⚠️ You reached the FREE daily limit ({FREE_LIMIT_PER_DAY}).\nUpgrade to PREMIUM 💎 or invite 2 friends 🎁.",
        "ru": f"⚠️ Вы достигли лимита FREE ({FREE_LIMIT_PER_DAY} в день).\nОформите PREMIUM 💎 или пригласите 2 друзей 🎁.",
        "tj": f"⚠️ Шумо лимити FREE-ро расидед ({FREE_LIMIT_PER_DAY} дар як рӯз).\nPREMIUM 💎 гиред ё 2 дӯстро даъват кунед 🎁.",
    },
    "skill_placeholder": {
        "en": "🚧 {skill} (Level: {lvl}) — coming soon with AI power 🤖",
        "ru": "🚧 {skill} (Уровень: {lvl}) — скоро будет с AI 🤖",
        "tj": "🚧 {skill} (Сатҳ: {lvl}) — ба зудӣ бо AI фаъол мешавад 🤖",
    },
    "writing_send_answer": {
        "en": "Send your answer as ONE message.",
        "ru": "Отправьте ваш ответ ОДНИМ сообщением.",
        "tj": "Ҷавобро дар ЯК паём фиристед.",
    },
}

# =========================
# Writing prompts (by level)
# =========================
WRITING_PROMPTS = {
    "A1": [
        "Write 5–7 sentences about your daily routine.",
        "Describe your family in 6–8 simple sentences.",
    ],
    "A2": [
        "Write about your favorite place in your city. (80–120 words)",
        "Describe a memorable day. (80–120 words)",
    ],
    "B1": [
        "Some people prefer studying alone. Others prefer studying with friends. What do you prefer and why? (120–170 words)",
        "Should students have part-time jobs? Give reasons and examples. (120–170 words)",
    ],
    "B2": [
        "Do the advantages of social media outweigh the disadvantages? Discuss both views and give your opinion. (200–260 words)",
        "Some people say university education should be free. Do you agree or disagree? (200–260 words)",
    ],
    "C1": [
        "In many countries, technology is changing the way people work. What are the long-term effects on society? (260–320 words)",
        "Should governments regulate AI more strictly? Discuss the benefits and risks. (260–320 words)",
    ],
    "C2": [
        "To what extent should individual freedom be limited for public safety? Provide a nuanced argument. (300–380 words)",
        "Is economic growth always beneficial? Evaluate with complex reasoning and examples. (300–380 words)",
    ],
}

# =========================
# HELPERS
# =========================
def lang_of(user_id: int) -> str:
    return user_lang.get(user_id, "en")

def today_str() -> str:
    return date.today().isoformat()

def ensure_user(user_id: int) -> None:
    user_plan.setdefault(user_id, "free")
    user_level.setdefault(user_id, "B1")
    user_mode.setdefault(user_id, "")

def plans_keyboard() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton("🌱 FREE", callback_data="plan_free")],
        [InlineKeyboardButton("💳 PREMIUM $1.99", callback_data="plan_premium_pay")],
        [InlineKeyboardButton("🎁 PREMIUM FREE (Invite 2)", callback_data="plan_premium_invite")],
    ]
    return InlineKeyboardMarkup(kb)

def level_keyboard() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton("A1 (Beginner)", callback_data="lvl_A1"),
         InlineKeyboardButton("A2 (Elementary)", callback_data="lvl_A2")],
        [InlineKeyboardButton("B1 (Intermediate)", callback_data="lvl_B1"),
         InlineKeyboardButton("B2 (Upper)", callback_data="lvl_B2")],
        [InlineKeyboardButton("C1 (Advanced)", callback_data="lvl_C1"),
         InlineKeyboardButton("C2 (Pro)", callback_data="lvl_C2")],
    ]
    return InlineKeyboardMarkup(kb)

def skills_keyboard() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton("🗣 Speaking", callback_data="skill_speaking")],
        [InlineKeyboardButton("🎧 Listening", callback_data="skill_listening")],
        [InlineKeyboardButton("📖 Reading", callback_data="skill_reading")],
        [InlineKeyboardButton("✍️ Writing", callback_data="skill_writing")],
    ]
    return InlineKeyboardMarkup(kb)

def can_use_free(user_id: int) -> bool:
    rec = free_usage.get(user_id, {"day": today_str(), "count": 0})
    if rec["day"] != today_str():
        rec = {"day": today_str(), "count": 0}
    if rec["count"] >= FREE_LIMIT_PER_DAY:
        free_usage[user_id] = rec
        return False
    rec["count"] += 1
    free_usage[user_id] = rec
    return True

def pick_prompt(level: str) -> str:
    level = level if level in WRITING_PROMPTS else "B1"
    return random.choice(WRITING_PROMPTS[level])

# --- Hybrid feedback (no API) ---
def simple_grammar_fix(text: str) -> str:
    fixes = {
        " i ": " I ",
        " im ": " I'm ",
        " dont ": " don't ",
        " cant ": " can't ",
        "wanna ": "want to ",
        "gonna ": "going to ",
        "doesnt ": "doesn't ",
        "didnt ": "didn't ",
        "ive ": "I've ",
        " its ": " it's ",
    }
    out = " " + text.strip() + " "
    for a, b in fixes.items():
        out = out.replace(a, b)
    return out.strip()

def advanced_vocab_suggestions(level: str):
    if level in ["A1", "A2"]:
        return ["good → great", "very big → huge", "a lot of → many"]
    if level in ["B1", "B2"]:
        return ["important → significant", "think → believe/argue", "good → beneficial"]
    return ["important → pivotal", "increase → escalate", "problem → challenge/concern"]

def estimate_scores(word_count: int, errors: int, level: str):
    base = {"A1": 3, "A2": 4, "B1": 5.5, "B2": 6.5, "C1": 7.5, "C2": 8.5}.get(level, 5.5)
    penalty = min(2.5, errors * 0.15)
    ielts = max(0.0, min(9.0, base - penalty))
    toefl = int(max(0, min(120, (ielts / 9) * 120)))
    det = int(max(10, min(160, (ielts / 9) * 160)))
    return round(ielts, 1), toefl, det

# =========================
# REFERRAL: /start <referrer_id>
# =========================
async def process_referral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        return
    try:
        referrer_id = int(context.args[0])
    except ValueError:
        return

    new_user_id = update.effective_user.id
    if referrer_id == new_user_id:
        return

    invited = ref_invited_users.setdefault(referrer_id, set())
    if new_user_id in invited:
        return

    invited.add(new_user_id)
    ref_count[referrer_id] = len(invited)

    if ref_count[referrer_id] >= 2 and user_plan.get(referrer_id) != "premium":
        user_plan[referrer_id] = "premium"
        ref_lang = lang_of(referrer_id)
        try:
            await context.bot.send_message(chat_id=referrer_id, text=TXT["invite_success_notify"][ref_lang])
        except Exception:
            pass

# =========================
# HANDLERS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(update.effective_user.id)
    await process_referral(update, context)

    kb = [
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
         InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("🇹🇯 Тоҷикӣ", callback_data="lang_tj")],
    ]
    await update.message.reply_text(TXT["start_choose_lang"]["en"], reply_markup=InlineKeyboardMarkup(kb))

async def on_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    lc = q.data.replace("lang_", "")
    user_lang[user_id] = lc
    ensure_user(user_id)

    lang = lang_of(user_id)
    await q.edit_message_text(
        text=f"{TXT['plan_title'][lang]}\n\n{TXT['plan_desc'][lang]}",
        reply_markup=plans_keyboard(),
    )

async def on_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    lang = lang_of(user_id)
    ensure_user(user_id)

    if q.data == "plan_free":
        user_plan[user_id] = "free"
        free_usage[user_id] = {"day": today_str(), "count": 0}
        await q.edit_message_text(text=TXT["choose_level_title"][lang], reply_markup=level_keyboard())
        return

    if q.data == "plan_premium_pay":
        await q.edit_message_text(text=TXT["premium_pay_info"][lang], reply_markup=plans_keyboard())
        return

    if q.data == "plan_premium_invite":
        bot_username = context.bot.username
        invite_link = f"https://t.me/{bot_username}?start={user_id}"
        count = ref_count.get(user_id, 0)
        msg = (
            f"{TXT['invite_info'][lang]}\n\n"
            f"{invite_link}\n\n"
            f"{TXT['invite_progress'][lang].format(count=count)}"
        )
        await q.edit_message_text(text=msg, reply_markup=plans_keyboard())
        return

async def on_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    lang = lang_of(user_id)
    ensure_user(user_id)

    lvl = q.data.replace("lvl_", "")
    user_level[user_id] = lvl

    await q.edit_message_text(
        text=TXT["level_saved"][lang].format(lvl=lvl),
        reply_markup=skills_keyboard(),
    )

async def on_skill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    lang = lang_of(user_id)
    ensure_user(user_id)

    plan = user_plan.get(user_id, "free")
    if plan != "premium":
        if not can_use_free(user_id):
            await q.edit_message_text(text=TXT["free_limit_reached"][lang], reply_markup=plans_keyboard())
            return

    lvl = user_level.get(user_id, "B1")
    skill = q.data.replace("skill_", "")

    # Writing flow
    if skill == "writing":
        prompt = pick_prompt(lvl)
        user_mode[user_id] = "writing_waiting"
        user_last_prompt[user_id] = prompt

        if lang == "en":
            msg = f"✍️ Writing Task ({lvl})\n\n{prompt}\n\n{TXT['writing_send_answer'][lang]}"
        elif lang == "ru":
            msg = f"✍️ Письменное задание ({lvl})\n\n{prompt}\n\n{TXT['writing_send_answer'][lang]}"
        else:
            msg = f"✍️ Супориши Writing ({lvl})\n\n{prompt}\n\n{TXT['writing_send_answer'][lang]}"

        await q.edit_message_text(text=msg)
        return

    # Other skills placeholder
    skill_name = skill.capitalize()
    await q.edit_message_text(
        text=TXT["skill_placeholder"][lang].format(skill=skill_name, lvl=lvl),
        reply_markup=skills_keyboard(),
    )

async def on_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(user_id)
    lang = lang_of(user_id)

    if user_mode.get(user_id) != "writing_waiting":
        return

    user_mode[user_id] = ""
    essay = (update.message.text or "").strip()

    word_count = len(essay.split())
    corrected = simple_grammar_fix(essay)

    errors = 0
    if corrected != essay:
        errors += 3
    if "  " in essay:
        errors += 1
    if essay.count(".") < 2 and word_count > 40:
        errors += 2

    lvl = user_level.get(user_id, "B1")
    ielts, toefl, det = estimate_scores(word_count, errors, lvl)
    vocab = advanced_vocab_suggestions(lvl)

    if lang == "en":
        msg = (
            f"✅ **Corrected Version (English):**\n{corrected}\n\n"
            f"📌 **Quick Feedback:**\n- Words: {word_count}\n- Estimated errors: {errors}\n\n"
            f"💎 **Advanced Vocabulary:**\n- " + "\n- ".join(vocab) + "\n\n"
            f"📊 **Approx. Scores:**\n- IELTS: {ielts}\n- TOEFL: {toefl}\n- Duolingo: {det}\n\n"
            f"⚠️ Note: scores are approximate."
        )
    elif lang == "ru":
        msg = (
            f"✅ **Исправленная версия (English):**\n{corrected}\n\n"
            f"📌 **Короткий feedback:**\n- Слова: {word_count}\n- Примерно ошибок: {errors}\n\n"
            f"💎 **Продвинутые слова:**\n- " + "\n- ".join(vocab) + "\n\n"
            f"📊 **Примерные баллы:**\n- IELTS: {ielts}\n- TOEFL: {toefl}\n- Duolingo: {det}\n\n"
            f"⚠️ Важно: оценки приблизительные."
        )
    else:
        msg = (
            f"✅ **Ислоҳшуда (English):**\n{corrected}\n\n"
            f"📌 **Feedback кӯтоҳ:**\n- Калимаҳо: {word_count}\n- Хатоҳо (тахминӣ): {errors}\n\n"
            f"💎 **Калимаҳои advanced:**\n- " + "\n- ".join(vocab) + "\n\n"
            f"📊 **Баҳои тахминӣ:**\n- IELTS: {ielts}\n- TOEFL: {toefl}\n- Duolingo: {det}\n\n"
            f"⚠️ Эзоҳ: баҳоҳо тахминӣ ҳастанд."
        )

    await update.message.reply_text(msg, parse_mode="Markdown")
    await update.message.reply_text(TXT["skills_title"][lang], reply_markup=skills_keyboard())

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_lang, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(on_plan, pattern="^plan_"))
    app.add_handler(CallbackQueryHandler(on_level, pattern="^lvl_"))
    app.add_handler(CallbackQueryHandler(on_skill, pattern="^skill_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_message))

    print("🤖 Fluentix AI is running...")
    app.run_polling()

if __name__ == "__main__":
    main()

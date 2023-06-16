#!/usr/bin/env python
# pylint: disable=unused-argument, wrong-import-position
# This program is dedicated to the public domain under the CC0 license.

"""
Basic example for a bot that works with polls. Only 3 people are allowed to interact with each
poll/quiz the bot generates. The preview command generates a closed poll/quiz, exactly like the
one the user sends the bot
"""
import logging
import requests

from telegram import __version__ as TG_VER
from supabase import create_client, Client

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import (
    KeyboardButton,
    KeyboardButtonPollType,
    Poll,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PollAnswerHandler,
    PollHandler,
    filters,
)

url: str = "https://nytkabvchpxcdysrbdfq.supabase.co"
key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im55dGthYnZjaHB4Y2R5c3JiZGZxIiwicm9sZSI6ImFub24iLCJpYXQiOjE2ODY4NzIwMDUsImV4cCI6MjAwMjQ0ODAwNX0.PtzpKaaUN8-K3iUASBS0K5qb9KHy79_-u4itBXX_8hY"
TOKEN = "6225524887:AAGrLG5b1Ucs7XtyfRhPiIEqT0WlTo7R4Cw"

def db_init():
    supabase: Client = create_client(url, key)

    return supabase

db = db_init()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


TOTAL_VOTER_COUNT = 3


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inform user about what this bot can do"""
    await update.message.reply_text(
        "Please select /poll to get a Poll, /quiz to get a Quiz or /preview"
        " to generate a preview for your poll"
    )


async def me(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # 获取并打印用户 id
    try :
        user_id = update.effective_user.id
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Your Telegram User ID: {user_id}")
        print(f"User ID: {user_id}")
    except Exception as e:
        print(f"Error fetching user id, Error: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Error occurred while fetching User ID.")
        return

async def poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # 从 Supabase 中获取投票信息
    try :
        result = db.table("polls").select("*").execute()
    except Exception as e:
        print(f"Error fetching data from Supabase, Error: {e}")
        return
    # 选择一个投票
    poll_data = result.data[-1]

    # 从 Supabase 数据中提取投票信息
    poll_title = poll_data["title"]
    poll_options = poll_data["options"]
    poll_only_members = poll_data["only_members"]
    poll_is_anonymous = poll_data["is_anonymous"]
    poll_allows_multiple_answers = poll_data["allows_multiple_answers"]

    poll_id = poll_data["id"]

    # 发起投票
    message = await context.bot.send_poll(
        update.effective_chat.id,
        poll_title,
        poll_options,
        is_anonymous=poll_is_anonymous,  # 投票不再匿名以记录投票者信息
        allows_multiple_answers=poll_allows_multiple_answers,
    )

    # 保存一些关于投票的信息，供稍后在 receive_poll_answer 中使用
    payload = {
        message.poll.id: {
            "questions": poll_options,
            "message_id": message.message_id,
            "chat_id": update.effective_chat.id,
            "answers": 0,
            "only_members": poll_only_members,
            "poll_id": poll_id
        }
    }
    context.bot_data.update(payload)


# async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     ## 进行投票限制
#     """Summarize a users poll vote"""
#     answer = update.poll_answer
#     answered_poll = context.bot_data[answer.poll_id]
#     try:
#         questions = answered_poll["questions"]
#     # this means this poll answer update is from an old poll, we can't do our answering then
#     except KeyError:
#         return
#     selected_options = answer.option_ids
#     answer_string = ""
#     for question_id in selected_options:
#         if question_id != selected_options[-1]:
#             answer_string += questions[question_id] + " and "
#         else:
#             answer_string += questions[question_id]
#     await context.bot.send_message(
#         answered_poll["chat_id"],
#         f"{update.effective_user.mention_html()} feels {answer_string}!",
#         parse_mode=ParseMode.HTML,
#     )
#     answered_poll["answers"] += 1
#     # Close poll after three participants voted
#     if answered_poll["answers"] == TOTAL_VOTER_COUNT:
#         await context.bot.stop_poll(answered_poll["chat_id"], answered_poll["message_id"])
async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("receive_poll_answer!")
    """Summarize a users poll vote"""
    answer = update.poll_answer
    poll_id = answer.poll_id
    try:
        voted_option = context.bot_data[poll_id]["questions"][answer.option_ids[0]]
    except KeyError:
        # this means this poll answer update is from an old poll, we can't do our answering then
        return

    # Get if this poll is members only
    only_members = context.bot_data[poll_id]["only_members"]
    poll_id = context.bot_data[poll_id]["poll_id"]

    if only_members:
        # Check if the user is a member
        member_result = db.table("members").select("*").filter(tg_user_id=answer.user.id).execute()
        print(member_result)
        if member_result.data is None or len(member_result.data) == 0:
            await context.bot.send_message(
                context.bot_data[poll_id]["chat_id"], "Only members can vote in this poll."
            )
            return

    # Save the vote in the poll_votes table
    try:
        db.table("poll_votes").insert({"poll_id": poll_id, "option": voted_option, "tg_user_id": answer.user.id}).execute()
    except Exception as e:
        print(f"Error saving vote to Supabase, Error: {e}")
        return

    # Send a message to say that the vote was received
    # context.bot.send_message(
    #     context.bot_data[poll_id]["chat_id"], f"Received {voted_option} from {answer.user.first_name}"
    # )


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a predefined poll"""
    questions = ["1", "2", "4", "20"]
    message = await update.effective_message.reply_poll(
        "How many eggs do you need for a cake?", questions, type=Poll.QUIZ, correct_option_id=2
    )
    # Save some info about the poll the bot_data for later use in receive_quiz_answer
    payload = {
        message.poll.id: {"chat_id": update.effective_chat.id, "message_id": message.message_id}
    }
    context.bot_data.update(payload)


async def receive_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Close quiz after three participants took it"""
    # the bot can receive closed poll updates we don't care about
    if update.poll.is_closed:
        return
    if update.poll.total_voter_count == TOTAL_VOTER_COUNT:
        try:
            quiz_data = context.bot_data[update.poll.id]
        # this means this poll answer update is from an old poll, we can't stop it then
        except KeyError:
            return
        await context.bot.stop_poll(quiz_data["chat_id"], quiz_data["message_id"])


async def preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask user to create a poll and display a preview of it"""
    # using this without a type lets the user chooses what he wants (quiz or poll)
    button = [[KeyboardButton("Press me!", request_poll=KeyboardButtonPollType())]]
    message = "Press the button to let the bot generate a preview for your poll"
    # using one_time_keyboard to hide the keyboard
    await update.effective_message.reply_text(
        message, reply_markup=ReplyKeyboardMarkup(button, one_time_keyboard=True)
    )


async def receive_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """On receiving polls, reply to it by a closed poll copying the received poll"""
    username = update.effective_user.username
    print("receive_poll user: ",username)
    actual_poll = update.effective_message.poll
    # Only need to set the question and options, since all other parameters don't matter for
    # a closed poll
    await update.effective_message.reply_poll(
        question=actual_poll.question,
        options=[o.text for o in actual_poll.options],
        # with is_closed true, the poll/quiz is immediately closed
        is_closed=True,
        reply_markup=ReplyKeyboardRemove(),
    )

def get_token():
    # 登录获取JWT令牌
    login_url = 'https://cdjozryigtcfpdhzwgwx.supabase.co/auth/v1/token?grant_type=password'  # 替换为实际的登录URL
    login_data = {
        'email': '673683677@qq.com',
        'password': '123456',
        'gotrue_meta_security': {}
    }
    apikey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNkam96cnlpZ3RjZnBkaHp3Z3d4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE2ODUwODc0MjEsImV4cCI6MjAwMDY2MzQyMX0.CvVWzFPy9GNkLD7qnVrnN38Zq8a0dg4BWujrDw-9T14'
    headers = {'apikey': f'{apikey}',
                'Authorization': f'Bearer {apikey}'
               }

    response = requests.post(login_url,headers=headers, json=login_data)
    # print(response.text)
    token = response.json()['access_token']
    return token


def ask_question(token, question):
    # 创建聊天消息
    chat_message = {
        'question': question,
        'history': [],
        "temperature":0,
        "max_tokens":500,
        'model': 'gpt-3.5-turbo'  # 你希望使用的模型名称
    }
    # 请求聊天接口
    chat_url = 'http://202.182.125.173/chat/'  # 替换为实际的聊天接口URL
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.post(chat_url, headers=headers, json=chat_message)
    # print(response.text)
    # 输出返回的历史记录
    history = response.json()['history']
    # Extract assistant value
    assistant_text =history[1][1]  # index 1 corresponds to the assistant's response
    # print(assistant_text)
    return assistant_text

async def chat(update: Update, context):
    question = update.message.text.split(' ', 1)[1]  # split the message into command and question, and get the question part
    token = get_token()
    answer = ask_question(token, question)
    await update.message.reply_text(answer)



async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display a help message"""
    await update.message.reply_text("Use /quiz, /poll or /preview to test this bot.")



def main() -> None:
    """Run bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("me", me))
    application.add_handler(CommandHandler("poll", poll))
    application.add_handler(CommandHandler("quiz", quiz))
    application.add_handler(CommandHandler("preview", preview))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(MessageHandler(filters.POLL, receive_poll))
    application.add_handler(PollAnswerHandler(receive_poll_answer))
    application.add_handler(PollHandler(receive_quiz_answer))
    application.add_handler(CommandHandler("chat", chat))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
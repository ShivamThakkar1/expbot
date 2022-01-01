import logging
from datetime import datetime, time

from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, JobQueue
from telegram.ext.jobqueue import Days

from connection import insert_player, get_player, gain_exp, check_player_level_up, get_top_ten, silence_chat, \
    check_silence, get_king

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


def start(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="I'm at your service, sir!\n"
                                  "This bot provide a rank system for your chat or group\n"
                                  "Automatically adds the players when they write the first message\n"
                                  "Chack your stats with /status and the chat ranks with /leaderboard")


def status(update: Update, context: CallbackContext):
    user = update.effective_message.from_user
    chat = update.effective_message.chat
    player = get_player(user.id, chat.id)
    if not player:
        update.message.reply_text("I don't know who you are!\n"
                                  "With the first non-command message you send I will register you!")
    else:
        update.message.reply_text("Hi {}, your current level is {}.\n"
                                  "You've earn {} experience in this group."
                                  .format(user.username, player.level, player.experience))


def echo(update: Update, context: CallbackContext):
    user = update.effective_message.from_user
    chat = update.effective_message.chat
    player = get_player(user.id, chat.id)
    if player is not None:
        if antiflood(user.id, chat.id):
            gain_exp(user.id, chat.id)
            level_up = check_player_level_up(user.id, chat.id)
            name = user.username if user.username else user.first_name
            if level_up and not check_silence(chat.id):
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text="{} you have gained enough experience to level up!\n"
                                              "Your current level is {}."
                                         .format(name, player.level + 1))
    else:
        insert_player(user.id, chat.id)
        gain_exp(user.id, chat.id)


def rank(update: Update, context: CallbackContext):
    chat = update.message.chat
    leaderboard = get_top_ten(chat.id)
    if not leaderboard:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="No one is currently registered! How dare you...")
    else:
        response = "Ladies and Gentlemen, this is the current leaderboard\n"
        i = 1
        name = None
        for player in leaderboard:
            if context.bot.getChatMember(chat.id, player.user_id).user.username:
                name = str(context.bot.getChatMember(chat.id, player.user_id).user.username)
            elif context.bot.getChatMember(chat.id, player.user_id).user.first_name:
                name = str(context.bot.getChatMember(chat.id, player.user_id).user.first_name)

            response = response + str(i) + "# place " + name + \
                       " al level " + str(player.level) + " (exp " + str(player.experience) + ")\n"
            i = i + 1
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=response)


bursts = {}


def antiflood(user_id, chat_id):
    key = f"{user_id}@{chat_id}"
    burst = bursts.get(key, {"begin": datetime.now(), "count": 0})

    if (datetime.now() - burst["begin"]).total_seconds() < 3:
        burst["count"] += 1
        bursts[key] = burst
        return burst["count"] < 5
    else:
        bursts[key] = {"begin": datetime.now(), "count": 1}
        return True


def silence(update: Update, context: CallbackContext):
    chat = update.message.chat
    check = silence_chat(chat.id)
    if check:
        context.bot.send_message(chat_id=update.effective_chat.id, text="I'm now in silence mode, please type "
                                                                        "/silence again to return in reply mode")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="I'm now in reply mode, please type "
                                                                        "/silence to shout me up")


def notify_king(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text="King mode is enabled")
    t = time(hour=10-2, minute=0, second=0, microsecond=0)
    print(t)
    print(datetime.utcnow())
    job = context.job_queue.run_daily(job_king, t, days=Days.EVERY_DAY, context=update.effective_chat.id, name="king")
    context.chat_data['job'] = job


def job_king(context: CallbackContext):
    job = context.job
    king = get_king(job.context)
    if not king:
        context.bot.send_message(chat_id=job.context,
                                 text='"And any man who must say "I am king" is no ' \
                                      'true king at all." - George R.R. Martin')
    elif not check_silence(job.context):
        name = None
        if context.bot.getChatMember(job.context, king.user_id).user.username:
            name = str(context.bot.getChatMember(job.context, king.user_id).user.username)
        elif context.bot.getChatMember(job.context, king.user_id).user.first_name:
            name = str(context.bot.getChatMember(job.context, king.user_id).user.first_name)
        context.bot.send_message(chat_id=job.context,
                                 text="Today's king is " + name + " at level " +
                                      str(king.level) + " (exp " + str(king.experience) +
                                      ")\nAll of you, kneel before him and commit yourselves to be crowned tomorrow")


updater = Updater(token='5052806486:AAHHPTFAHSOZ6hrCexLM8kCmSaSuZvU-2S8', use_context=True)


def main():
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('status', status))
    dp.add_handler(CommandHandler('leaderboard', rank))
    dp.add_handler(CommandHandler('silence', silence))
    dp.add_handler(CommandHandler('notify_king', notify_king,
                                  pass_args=True, pass_job_queue=True, pass_chat_data=True))
    #dp.add_handler(CommandHandler('king', king))
    dp.add_handler(MessageHandler((~Filters.command) & (~Filters.update.edited_message), echo))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

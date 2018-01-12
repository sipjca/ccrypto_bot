from telegram import ParseMode
from sqlalchemy import Column, Integer, Float, ForeignKey, String, create_engine
from sqlalchemy.orm import relationship
import re

import config
from coin import Coin, get_coin_from_input
from user import get_or_create_user
from db_base import Base, Session, engine, session

import logging

# engine = create_engine(config.build_db)
Base.metadata.bind = engine

class Wallet(Base):
    __tablename__ = 'wallet'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    coin_id = Column(Integer, ForeignKey('coin.id'))
    user = relationship("User", back_populates="wallets")
    coin = relationship("Coin", back_populates="wallets")

    amount = Column(Integer, nullable=False)
    send_addr = Column(String, nullable=True)
    recieve_addr = Column(String, nullable=True)
    stored_on = Column(String(50), nullable=True)

    def __init__(self, user, coin, amount, send = None, recieve = None, store = None):
        self.user = user
        self.coin = coin
        self.amount = amount
        self.send_addr = send
        self.recieve_addr = recieve
        self.stored_on = store 

def wallet(bot, update):
    user = get_or_create_user(update.message.from_user)
    wallets = session.query(Wallet).filter((Wallet.user == user) &\
                                     (Wallet.amount > 0)).all()
    if len(wallets) == 0:
        message = "You have no coins in your portfolio"
    else:
        message = "<b>{}'s Portfolio</b>".format(user.first_name)
        total_value = 0
        total_change = 0
        for w in wallets:
            amount_val = w.coin.price_usd*w.amount
            dollar_change = amount_val*(w.coin.change_24h/100)

            total_value += amount_val
            total_change += dollar_change

            message += "\n{} {}: ${:,} (${:,})".format(w.amount, w.coin.symbol, round(amount_val,2), round(dollar_change,2))
        message += "\n\nUSD Change over 24h: ${:,}".format(round(total_change,2))
        message += "\nTotal Value: <b>${:,}</b>".format(round(total_value,2))
    bot.send_message(chat_id=update.message.chat_id,
                     text=message,
                     parse_mode=ParseMode.HTML)

def wallet_message_handler(bot, update):
    message_list = update.message.text.split()
    if message_list[0] not in ['add', 'bought', 'buy', 'sold', 'sell', 'remove', 'trade', 'traded', 'exchanged', 'exchange']:
        return

    # Check if user exists in db
    user = get_or_create_user(update.message.from_user)

    # This will take the message, convert it into an action and return the 
    # response from the action
    message = get_message(message_list, user)
    if message is None:
        return
    update.message.reply_text(message)

def get_message(input, user):
    # We do this so that we can not accidentally add
    if input[0].lower() in ['add', 'bought', 'buy']:
        message = add_coin(user, input)
    elif input[0].lower() in ['sold', 'sell', 'remove']:
        message = remove_coin(user, input)
    elif input[0].lower() in ['trade', 'traded', 'exchange', 'exchanged']:
        message = trade_coin(user, input)
    else:
        return None
    return message

def add_coin(user, input):
    num, coin_string = get_num_coins(input)
    coin = get_coin_from_input(coin_string)

    wallet = session.query(Wallet).filter((Wallet.user == user) &\
                                          (Wallet.coin == coin)).first()

    # if the user has this coin simply add to it, otherwise set it up
    if wallet:
        wallet.amount += num
        session.commit()
    else:
        wallet = Wallet(user, coin, num)
        session.add(wallet)
        session.commit()
    return "{} {} added".format(round(num,3), coin.symbol)

def remove_coin(user, input):
    num, coin_string = get_num_coins(input)
    coin = get_coin_from_input(coin_string)

    wallet = session.query(Wallet).filter((Wallet.user == user) &\
                                          (Wallet.coin == coin)).first()
    if wallet:
        if num == "all":
            return_string = "You have sold all of your {} {}".format(wallet.amount, coin.symbol)
            wallet.amount = 0.0
            session.commit()
            return return_string
        else:
            wallet.amount -= num
            session.commit()
            return "You have sold {} of your {}. {} {} remaining".format(round(num,3), coin.symbol, round(wallet.amount,3), coin.symbol)
    else:
        # dont remove someting thats not there
        return "You have no {} to remove you big dumb baby".format(coin.symbol)

def trade_coin(user, input):
    # this takes the form of something like trade 10 eth to 100000 gnt
    pass

def get_num_coins(input):
    if len(input) == 3:
        if input[1] == 'all':
            num = input[1]
        else:
            num = float(input[1])
        coin = input[2].upper()
    else:
        num_coins = re.findall('\d+|\D+', input[1])
        num = float(num_coins[0])
        coin = num_coins[1].upper()

    return num, coin


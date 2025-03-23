import logging
import asyncio
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# კონფიგურაცია
API_TOKEN = V
ADMIN_USER_ID = Vintagebot  # ჩაანაცვლეთ თქვენი ტელეგრამის ID-ით

# მონაცემთა ბაზის იმიტაცია (რეალურ აპლიკაციაში უნდა გამოიყენოთ ნამდვილი ბაზა)
users_db = {}
songs_db = [
    {"id": 1, "title": "მუსიკა 1", "artist": "შემსრულებელი 1", "duration": 180, "coins": 5},
    {"id": 2, "title": "მუსიკა 2", "artist": "შემსრულებელი 2", "duration": 210, "coins": 6},
    {"id": 3, "title": "მუსიკა 3", "artist": "შემსრულებელი 3", "duration": 240, "coins": 7},
    {"id": 4, "title": "მუსიკა 4", "artist": "შემსრულებელი 4", "duration": 190, "coins": 5},
    {"id": 5, "title": "მუსიკა 5", "artist": "შემსრულებელი 5", "duration": 200, "coins": 6},
]

# ლოგირების კონფიგურაცია
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ბოტის ინიციალიზაცია
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# სტატუსების კლასი
class UserStates(StatesGroup):
    listening = State()
    menu = State()
    shop = State()

# მომხმარებლის მოდელი
class User:
    def __init__(self, user_id, username):
        self.user_id = user_id
        self.username = username
        self.coins = 0
        self.energy = 100
        self.last_energy_update = datetime.now()
        self.current_song = None
        self.listening_start_time = None
        self.daily_listened = 0
        self.daily_reset = datetime.now()
        self.items = []

    def update_energy(self):
        now = datetime.now()
        if self.last_energy_update:
            # ყოველ 5 წუთში 1 ენერგიის აღდგენა
            minutes_passed = (now - self.last_energy_update).total_seconds() / 60
            energy_to_add = int(minutes_passed / 5)
            
            if energy_to_add > 0:
                self.energy = min(100, self.energy + energy_to_add)
                self.last_energy_update = now

    def reset_daily_if_needed(self):
        now = datetime.now()
        if now.date() > self.daily_reset.date():
            self.daily_listened = 0
            self.daily_reset = now
            return True
        return False

# კლავიატურის შექმნის ფუნქციები
def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🎵 მოუსმინე მუსიკას", callback_data="listen"),
        InlineKeyboardButton("🏪 მაღაზია", callback_data="shop"),
        InlineKeyboardButton("👤 პროფილი", callback_data="profile"),
        InlineKeyboardButton("📊 რეიტინგი", callback_data="leaderboard")
    )
    return keyboard

def get_songs_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    for song in songs_db:
        keyboard.add(
            InlineKeyboardButton(
                f"{song['title']} - {song['artist']} ({song['duration']//60}:{song['duration']%60:02d}) - {song['coins']} 🪙", 
                callback_data=f"song_{song['id']}"
            )
        )
    keyboard.add(InlineKeyboardButton("🔙 მთავარ მენიუში", callback_data="back_to_main"))
    return keyboard

def get_shop_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("⚡ ენერგია +50 (100 🪙)", callback_data="buy_energy"),
        InlineKeyboardButton("⏱ დროის ამაჩქარებელი (200 🪙)", callback_data="buy_booster"),
        InlineKeyboardButton("🌟 VIP სტატუსი (500 🪙)", callback_data="buy_vip"),
        InlineKeyboardButton("🔙 მთავარ მენიუში", callback_data="back_to_main")
    )
    return keyboard

def get_listening_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("⏹ შეწყვეტა", callback_data="stop_listening"),
        InlineKeyboardButton("ℹ️ ინფორმაცია", callback_data="song_info")
    )
    return keyboard

# კომანდების ჰენდლერები
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    if user_id not in users_db:
        users_db[user_id] = User(user_id, username)
        await message.answer(
            f"მოგესალმები {username}! 👋\n\n"
            f"ეს არის მუსიკალური თამაში, სადაც შეგიძლია:\n"
            f"- მოუსმინო მუსიკას და მიიღო მონეტები 🪙\n"
            f"- შეიძინო სხვადასხვა ნივთები მაღაზიაში 🏪\n"
            f"- შეადარო შენი მიღწევები სხვებს 📊\n\n"
            f"დაიწყე ახლავე მუსიკის მოსმენით!", 
            reply_markup=get_main_keyboard()
        )
    else:
        user = users_db[user_id]
        user.update_energy()
        user.reset_daily_if_needed()
        
        await message.answer(
            f"მოგესალმები ისევ, {username}! 👋\n\n"
            f"შენი ბალანსი: {user.coins} 🪙\n"
            f"ენერგია: {user.energy}/100 ⚡\n\n"
            f"რისი გაკეთება გსურს?",
            reply_markup=get_main_keyboard()
        )

@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    await message.answer(
        "🎮 თამაშის წესები:\n\n"
        "1. მოუსმინე მუსიკას და მიიღე მონეტები 🪙\n"
        "2. ყოველ მოსმენაზე იხარჯება ენერგია ⚡\n"
        "3. ენერგია თავისით ივსება დროთა განმავლობაში\n"
        "4. შეგიძლია იყიდო ნივთები მაღაზიაში\n"
        "5. ყოველდღიური ლიმიტი: 20 სიმღერა\n\n"
        "ბრძანებები:\n"
        "/start - თამაშის დაწყება\n"
        "/profile - შენი პროფილის ნახვა\n"
        "/shop - მაღაზიაში შესვლა\n"
        "/help - ეს ინფორმაცია",
        reply_markup=get_main_keyboard()
    )

@dp.message_handler(commands=['profile'])
async def cmd_profile(message: types.Message):
    user_id = message.from_user.id
    if user_id in users_db:
        user = users_db[user_id]
        user.update_energy()
        user.reset_daily_if_needed()
        
        items_text = "არაფერი" if not user.items else ", ".join(user.items)
        
        await message.answer(
            f"👤 *შენი პროფილი*\n\n"
            f"სახელი: {user.username}\n"
            f"მონეტები: {user.coins} 🪙\n"
            f"ენერგია: {user.energy}/100 ⚡\n"
            f"დღეს მოსმენილი: {user.daily_listened}/20 🎵\n"
            f"შენი ნივთები: {items_text}\n\n"
            f"რისი გაკეთება გსურს შემდეგ?",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer(
            "გთხოვთ, ჯერ დაიწყეთ თამაში /start ბრძანებით."
        )

# კოლბექების ჰენდლერები
@dp.callback_query_handler(lambda c: c.data == 'listen', state='*')
async def process_listen(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user = users_db.get(user_id)
    
    if not user:
        await callback_query.answer("გთხოვთ, ჯერ დაიწყეთ თამაში /start ბრძანებით.")
        return
    
    user.update_energy()
    user.reset_daily_if_needed()
    
    if user.daily_listened >= 20:
        await callback_query.answer("დღეს უკვე მიაღწიე ლიმიტს (20 სიმღერა). სცადე ხვალ!")
        return
    
    if user.energy < 10:
        await callback_query.answer("არ გაქვს საკმარისი ენერგია. დაელოდე აღდგენას ან იყიდე მაღაზიაში.")
        return
    
    await callback_query.message.edit_text(
        "აირჩიე სიმღერა მოსასმენად:",
        reply_markup=get_songs_keyboard()
    )
    await UserStates.menu.set()

@dp.callback_query_handler(lambda c: c.data.startswith('song_'), state=UserStates.menu)
async def process_song_selection(callback_query: types.CallbackQuery, state: FSMContext):
    song_id = int(callback_query.data.split('_')[1])
    user_id = callback_query.from_user.id
    user = users_db.get(user_id)
    
    selected_song = None
    for song in songs_db:
        if song['id'] == song_id:
            selected_song = song
            break
    
    if not selected_song:
        await callback_query.answer("სიმღერა ვერ მოიძებნა. სცადე სხვა.")
        return
    
    if user.energy < 10:
        await callback_query.answer("არ გაქვს საკმარისი ენერგია!")
        return
    
    # სიმღერის მოსმენის დაწყება
    user.current_song = selected_song
    user.listening_start_time = datetime.now()
    user.energy -= 10
    user.last_energy_update = datetime.now()
    
    # მოსმენის სიმულაცია - რეალურად აქ უნდა იყოს მუსიკის URL ან ფაილი
    listening_message = await callback_query.message.edit_text(
        f"🎵 ახლა ისმენ: *{selected_song['title']}* - {selected_song['artist']}\n\n"
        f"⏳ ხანგრძლივობა: {selected_song['duration']//60}:{selected_song['duration']%60:02d}\n"
        f"💰 მოსალოდნელი მონეტები: {selected_song['coins']} 🪙\n\n"
        f"გთხოვთ, დაელოდეთ სიმღერის დასრულებას...",
        parse_mode="Markdown",
        reply_markup=get_listening_keyboard()
    )
    
    # შევინახოთ სტეიტში
    await state.update_data(
        song_id=song_id,
        message_id=listening_message.message_id,
        listening_start=user.listening_start_time.timestamp()
    )
    
    await UserStates.listening.set()

@dp.callback_query_handler(lambda c: c.data == 'stop_listening', state=UserStates.listening)
async def process_stop_listening(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user = users_db.get(user_id)
    
    if not user or not user.current_song:
        await callback_query.answer("არ მოისმენს სიმღერას ამჟამად.")
        await UserStates.menu.set()
        return
    
    # გამოთვალე რამდენი ხანი მოისმინა
    now = datetime.now()
    listened_time = (now - user.listening_start_time).total_seconds()
    song_duration = user.current_song['duration']
    
    if listened_time < song_duration * 0.5:
        # მინიმუმ ნახევარი უნდა მოუსმინოს მონეტების მისაღებად
        await callback_query.message.edit_text(
            "🛑 მოსმენა შეწყვეტილია. მონეტების მისაღებად უნდა მოუსმინო სიმღერის მინიმუმ ნახევარს.",
            reply_markup=get_main_keyboard()
        )
    else:
        # მონეტების რაოდენობა დამოკიდებულია მოსმენილ დროზე
        coins_earned = int(user.current_song['coins'] * min(1, listened_time / song_duration))
        user.coins += coins_earned
        user.daily_listened += 1
        
        await callback_query.message.edit_text(
            f"✅ მოსმენა დასრულებულია!\n\n"
            f"მოგებული მონეტები: {coins_earned} 🪙\n"
            f"ახალი ბალანსი: {user.coins} 🪙\n"
            f"დარჩენილი ენერგია: {user.energy} ⚡",
            reply_markup=get_main_keyboard()
        )
    
    user.current_song = None
    user.listening_start_time = None
    await UserStates.menu.set()

# ავტომატური დასრულების სიმულაცია - რეალურ აპლიკაციაში ეს უნდა შესრულდეს სხვა გზით
async def check_listening_sessions():
    while True:
        try:
            current_time = datetime.now()
            for user_id, user in users_db.items():
                if user.current_song and user.listening_start_time:
                    listened_time = (current_time - user.listening_start_time).total_seconds()
                    if listened_time >= user.current_song['duration']:
                        # სიმღერა დასრულდა, მიანიჭე მონეტები
                        user.coins += user.current_song['coins']
                        user.daily_listened += 1
                        
                        # შეტყობინება გაუგზავნე მომხმარებელს
                        try:
                            await bot.send_message(
                                user_id,
                                f"✅ სიმღერა დასრულდა: {user.current_song['title']}\n\n"
                                f"მოგებული მონეტები: {user.current_song['coins']} 🪙\n"
                                f"ახალი ბალანსი: {user.coins} 🪙\n"
                                f"დარჩენილი ენერგია: {user.energy} ⚡",
                                reply_markup=get_main_keyboard()
                            )
                        except Exception as e:
                            logger.error(f"Error sending message: {e}")
                        
                        user.current_song = None
                        user.listening_start_time = None
                
                # ენერგიის აღდგენა
                user.update_energy()
                
        except Exception as e:
            logger.error(f"Error in background task: {e}")
        
        await asyncio.sleep(5)  # შეამოწმე ყოველ 5 წამში

@dp.callback_query_handler(lambda c: c.data == 'shop', state='*')
async def process_shop(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user = users_db.get(user_id)
    
    if not user:
        await callback_query.answer("გთხოვთ, ჯერ დაიწყეთ თამაში /start ბრძანებით.")
        return
    
    await callback_query.message.edit_text(
        f"🏪 *მაღაზია*\n\n"
        f"შენი ბალანსი: {user.coins} 🪙\n\n"
        f"აირჩიე ნივთი შესაძენად:",
        parse_mode="Markdown",
        reply_markup=get_shop_keyboard()
    )
    await UserStates.shop.set()

@dp.callback_query_handler(lambda c: c.data.startswith('buy_'), state=UserStates.shop)
async def process_buy(callback_query: types.CallbackQuery, state: FSMContext):
    item = callback_query.data.split('_')[1]
    user_id = callback_query.from_user.id
    user = users_db.get(user_id)
    
    if not user:
        await callback_query.answer("გთხოვთ, ჯერ დაიწყეთ თამაში.")
        return
    
    price = 0
    item_name = ""
    success_message = ""
    
    if item == "energy":
        price = 100
        item_name = "ენერგიის შევსება"
        if user.coins >= price:
            user.coins -= price
            user.energy = min(100, user.energy + 50)
            success_message = f"⚡ შეიძინე +50 ენერგია! ახალი მაჩვენებელი: {user.energy}/100"
        
    elif item == "booster":
        price = 200
        item_name = "დროის ამაჩქარებელი"
        if user.coins >= price:
            user.coins -= price
            user.items.append("დროის ამაჩქარებელი")
            success_message = "⏱ შეიძინე დროის ამაჩქარებელი! ახლა სიმღერებს 2-ჯერ უფრო სწრაფად მოისმენ."
        
    elif item == "vip":
        price = 500
        item_name = "VIP სტატუსი"
        if user.coins >= price:
            user.coins -= price
            user.items.append("VIP სტატუსი")
            success_message = "🌟 შეიძინე VIP სტატუსი! ახლა მიიღებ +50% მეტ მონეტებს ყველა სიმღერაზე."
    
    if success_message:
        await callback_query.answer(f"წარმატებით შეიძინე: {item_name}")
        await callback_query.message.edit_text(
            f"{success_message}\n\n"
            f"დარჩენილი ბალანსი: {user.coins} 🪙",
            reply_markup=get_main_keyboard()
        )
        await UserStates.menu.set()
    else:
        await callback_query.answer(f"არ გაქვს საკმარისი მონეტები. საჭიროა {price} 🪙.")

@dp.callback_query_handler(lambda c: c.data == 'profile', state='*')
async def process_profile(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    if user_id in users_db:
        user = users_db[user_id]
        user.update_energy()
        user.reset_daily_if_needed()
        
        items_text = "არაფერი" if not user.items else ", ".join(user.items)
        
        await callback_query.message.edit_text(
            f"👤 *შენი პროფილი*\n\n"
            f"სახელი: {user.username}\n"
            f"მონეტები: {user.coins} 🪙\n"
            f"ენერგია: {user.energy}/100 ⚡\n"
            f"დღეს მოსმენილი: {user.daily_listened}/20 🎵\n"
            f"შენი ნივთები: {items_text}",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    else:
        await callback_query.answer("გთხოვთ, ჯერ დაიწყეთ თამაში /start ბრძანებით.")

@dp.callback_query_handler(lambda c: c.data == 'leaderboard', state='*')
async def process_leaderboard(callback_query: types.CallbackQuery, state: FSMContext):
    # რეიტინგის სორტირება მონეტების მიხედვით
    sorted_users = sorted(users_db.values(), key=lambda u: u.coins, reverse=True)
    
    leaderboard_text = "📊 *მოთამაშეების რეიტინგი*\n\n"
    
    for i, user in enumerate(sorted_users[:10], 1):
        leaderboard_text += f"{i}. {user.username}: {user.coins} 🪙\n"
    
    if not sorted_users:
        leaderboard_text += "რეიტინგში ჯერ არავინაა."
    
    await callback_query.message.edit_text(
        leaderboard_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query_handler(lambda c: c.data == 'back_to_main', state='*')
async def process_back_to_main(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user = users_db.get(user_id, None)
    
    if user:
        user.update_energy()
        await callback_query.message.edit_text(
            f"მთავარი მენიუ\n\n"
            f"მონეტები: {user.coins} 🪙\n"
            f"ენერგია: {user.energy}/100 ⚡\n\n"
            f"რისი გაკეთება გსურს?",
            reply_markup=get_main_keyboard()
        )
    else:
        await callback_query.message.edit_text(
            "მთავარი მენიუ\n\n"
            "გთხოვთ, დაიწყეთ თამაში /start ბრძანებით.",
            reply_markup=get_main_keyboard()
        )
    
    await UserStates.menu.set()

# ძირითადი ბრძანება ბოტის გასაშვებად
async def main():
    # ფონური ტასკი სიმღერების შესამოწმებლად
    asyncio.create_task(check_listening_sessions())
    
    # პოლინგის დაწყება
    await dp.start_polling()

if __name__ == '__main__':
    asyncio.run(main())

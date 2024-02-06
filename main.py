from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, InlineQueryHandler, \
    CallbackQueryHandler
from project.db import DB
from project.globals import TEXTS
from geopy.geocoders import Nominatim
from telegram import Location

db = DB()


async def start(update, context):
    user = update.message.from_user
    user_data = db.get_user(user.id)
    if not user_data:
        user_data = db.add_user(user.id, user.first_name, user.username)
        state = db.get_state(user_data['id'])
        if not state:
            state = db.add_state(user_data['id'], 1)
        lang_button = [
            [
                InlineKeyboardButton('🇺🇿 Uzbek', callback_data='lang_1'),
                InlineKeyboardButton('🇷🇺 Russian', callback_data='lang_2'),
                InlineKeyboardButton('🇺🇸 English', callback_data='lang_3')
            ]
        ]
        await update.message.reply_text("<b>Keling, avvaliga xizmat ko’rsatish tilini tanlab olaylik.</b>\n\n"
                                        "<b>Давайте для начала выберем язык обслуживания!</b>\n\n"
                                        "<b>Let's first choose the service language!</b>",
                                        parse_mode="HTML",
                                        reply_markup=InlineKeyboardMarkup(lang_button))
    else:
        if not user_data['lang']:
            state = db.get_state(user_data['id'])
            if not state:
                state = db.add_state(user_data['id'], 1)
            lang_button = [
                [
                    InlineKeyboardButton('🇺🇿 Uzbek', callback_data='lang_1'),
                    InlineKeyboardButton('🇷🇺 Russian', callback_data='lang_2'),
                    InlineKeyboardButton('🇺🇸 English', callback_data='lang_3')
                ]
            ]
            await update.message.reply_text("<b>Keling, avvaliga xizmat ko’rsatish tilini tanlab olaylik.</b>\n\n"
                                            "<b>Давайте для начала выберем язык обслуживания!</b>\n\n"
                                            "<b>Let's first choose the service language!</b>",
                                            parse_mode="HTML",
                                            reply_markup=InlineKeyboardMarkup(lang_button))
        elif not user_data['name']:
            db.add_state(user_data['id'], 2)
            await update.message.reply_text(TEXTS['TEXT_NAME'][user_data['lang']])

        elif not user_data['phone_number']:
            button = [
                [KeyboardButton(TEXTS['BTN_PHONE_NUMBER'][user_data['lang']], request_contact=True)]
            ]
            db.add_state(user_data['id'], 3)
            await update.message.reply_text(TEXTS['TEXT_PHONE_NUMBER'][user_data['lang']],
                                            reply_markup=ReplyKeyboardMarkup(button,
                                                                             resize_keyboard=True), parse_mode="HTML")
        else:
            db.clear_bucket(user_data['id'])
            buttons = [
                [
                    KeyboardButton(TEXTS['BTN_ORDER'][user_data['lang']]),
                    KeyboardButton(TEXTS['BTN_MY_ORDER'][user_data['lang']])
                ],
                [
                    KeyboardButton(TEXTS['BTN_FILIAL'][user_data['lang']])
                ]
            ]
            db.add_state(user_data['id'], 4)
            await update.message.reply_text(TEXTS['TEXT_MAIN_MENU'][user_data['lang']],
                                            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True),
                                            parse_mode="HTML")


async def message_handler(update, context):
    text = update.message.text
    user = update.message.from_user
    user_data = db.get_user(user.id)
    state = db.get_state(user_data['id'])
    lang = user_data['lang']

    if state['state'] == 2:
        user_data = db.update_user(user_data['id'], name=text)
        button = [
            [KeyboardButton(TEXTS['BTN_PHONE_NUMBER'][lang], request_contact=True)]
        ]
        db.add_state(user_data['id'], 3)
        await update.message.reply_text(TEXTS['TEXT_PHONE_NUMBER'][lang],
                                        reply_markup=ReplyKeyboardMarkup(button,
                                                                         resize_keyboard=True), parse_mode="HTML")
    elif state['state'] == 4:
        if text == TEXTS['BTN_ORDER'][lang]:
            categories = db.get_all_category()
            category_buttons = []
            temp_button = []
            for category in categories:
                temp_button.append(
                    InlineKeyboardButton(text=category['name'], callback_data=f"category_{category['id']}"))
                if len(temp_button) == 2:
                    category_buttons.append(temp_button)
                    temp_button = []
            if len(temp_button) > 0:
                category_buttons.append(temp_button)
            if db.get_bucket_items(user_data['id']):
                category_buttons.append([InlineKeyboardButton(TEXTS['BTN_BUCKET'][lang], callback_data="bucket_view")])
            await update.message.reply_text(TEXTS['TEXT_MAIN_MENU_1'][lang], reply_markup=ReplyKeyboardMarkup([[
                KeyboardButton(TEXTS['BTN_MAIN_MENU'][lang])
            ]], resize_keyboard=True))
            await update.message.reply_text(
                TEXTS['TEXT_MAIN_MENU_2'][lang],
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(category_buttons))

        elif text == TEXTS['BTN_MY_ORDER'][lang]:
            orders = db.get_my_order(user_data['id'])
            if orders:
                for order in orders:
                    summa = 0
                    text = (f"{TEXTS['TEXT_ORDER_NUMBER'][lang]} {order['order_id']}\n\n"
                            f"{TEXTS['LOCATION'][lang]} {order['location']}\n\n")
                    for item in order['items']:
                        item_data = db.get_order_item(item)
                        summa += item_data['count'] * item_data['product_price']
                        text += (f"{item_data['product_name']}\n{item_data['count']} ✖️ {item_data['product_price']} 🟰 "
                                 f"{item_data['count'] * item_data['product_price']}\n")
                    text += f"\n{TEXTS['TEXT_CREATED_DATE'][lang]} {order['created_date'].strftime('%d/%m/%Y %H:%M')}"
                    text += f"\n{TEXTS['TEXT_TOTAL_PRICE'][lang]} {summa} {TEXTS['TEXT_MONEY'][lang]}"
                    await update.message.reply_text(text)
            else:
                await update.message.reply_text(TEXTS['TEXT_NOT_ORDERS'][lang])

        elif text == TEXTS['BTN_FILIAL'][lang]:
            branchs = db.get_all_branch()
            branch_button = []
            temp_button = []
            temp_button.append(InlineKeyboardButton(TEXTS['BTN_BACK'][lang], callback_data="product_back"))
            for branch in branchs:
                temp_button.append(
                    InlineKeyboardButton(text=branch['name'], callback_data=f"branch_{branch['id']}"))
                if len(temp_button) == 2:
                    branch_button.append(temp_button)
                    temp_button = []
            if len(temp_button) > 0:
                branch_button.append(temp_button)
            await update.message.reply_text(TEXTS['TEXT_BRANCH'][lang],
                                            reply_markup=InlineKeyboardMarkup(branch_button))

        elif text == TEXTS['BTN_MAIN_MENU'][lang]:
            buttons = [
                [
                    KeyboardButton(TEXTS['BTN_ORDER'][user_data['lang']]),
                    KeyboardButton(TEXTS['BTN_MY_ORDER'][user_data['lang']])
                ],
                [
                    KeyboardButton(TEXTS['BTN_FILIAL'][user_data['lang']])
                ]
            ]

            db.add_state(user_data['id'], 4)
            await update.message.reply_text(TEXTS['TEXT_MAIN_MENU'][user_data['lang']],
                                            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True),
                                            parse_mode="HTML")


async def query_handler(update, context):
    data = update.callback_query.data
    user = update.callback_query.from_user
    data = data.split('_')
    print(data)
    user_data = db.get_user(user.id)
    lang = user_data['lang']
    message_id = update.callback_query.message.message_id
    state = db.get_state(user_data['id'])

    if data[0] == 'lang':
        user_data = db.update_user(user_data['id'], lang=data[1])
        db.add_state(user_data['id'], 2)
        await context.bot.delete_message(chat_id=user.id, message_id=message_id)
        await update.callback_query.message.reply_text(TEXTS['TEXT_NAME'][user_data['lang']])
    elif data[0] == 'category':
        products = db.get_all_product(int(data[1]))
        products_buttons = []
        temp_button = []
        for product in products:
            temp_button.append(
                InlineKeyboardButton(text=product['name'], callback_data=f"product_{product['id']}"))
            if len(temp_button) == 2:
                products_buttons.append(temp_button)
                temp_button = []
        if len(temp_button) > 0:
            products_buttons.append(temp_button)
        if db.get_bucket_items(user_data['id']):
            products_buttons.append([InlineKeyboardButton(TEXTS['BTN_BUCKET'][lang], callback_data="bucket_view")])
        products_buttons.append([InlineKeyboardButton(TEXTS['BTN_BACK'][lang], callback_data="product_back")])
        category = db.get_one_category(int(data[1]))
        await context.bot.delete_message(chat_id=user.id, message_id=message_id)
        await update.callback_query.message.reply_photo(photo=open(category['photo'], 'rb'),
                                                        caption=category['name'],
                                                        reply_markup=InlineKeyboardMarkup(products_buttons))
    elif data[0] == 'product':
        if data[1] == 'back':
            categories = db.get_all_category()
            category_buttons = []
            temp_button = []
            for category in categories:
                temp_button.append(
                    InlineKeyboardButton(text=category['name'], callback_data=f"category_{category['id']}"))
                if len(temp_button) == 2:
                    category_buttons.append(temp_button)
                    temp_button = []
            if len(temp_button) >= 1:
                category_buttons.append(temp_button)
            if db.get_bucket_items(user_data['id']):
                category_buttons.append([InlineKeyboardButton(TEXTS['BTN_BUCKET'][lang], callback_data="bucket_view")])

            await context.bot.delete_message(chat_id=user.id, message_id=message_id)
            await update.callback_query.message.reply_text(
                TEXTS['TEXT_MAIN_MENU_2'][lang],
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(category_buttons))
        else:
            product = db.get_one_product(int(data[1]))
            product_buttons = [
                [
                    InlineKeyboardButton("➖", callback_data=f"bucket_minus_{product['id']}_1"),
                    InlineKeyboardButton("1", callback_data="count"),
                    InlineKeyboardButton("➕", callback_data=f"bucket_plus_{product['id']}_1")
                ],
                [
                    InlineKeyboardButton(TEXTS['BTN_ADD_BUCKET'][lang], callback_data=f"bucket_add_{product['id']}_1")
                ],
                [
                    InlineKeyboardButton(TEXTS['BTN_BACK'][lang], callback_data=f"bucket_back_{product['id']}")
                ]
            ]
            if db.get_bucket_items(user_data['id']):
                product_buttons[2].append(InlineKeyboardButton(TEXTS['BTN_BUCKET'][lang], callback_data="bucket_view"))
            caption_text = TEXTS['TEXT_PRODUCT_CAPTION'][lang] % (
                product['name'], product['price'], product['description'])

            await context.bot.delete_message(chat_id=user.id, message_id=message_id)
            await update.callback_query.message.reply_photo(photo=open(product['photo'], 'rb'),
                                                            caption=caption_text,
                                                            reply_markup=InlineKeyboardMarkup(product_buttons))
    elif data[0] == 'bucket':
        if data[1] == 'plus':
            product = db.get_one_product(int(data[2]))
            product_count = int(data[3]) + 1
            product_buttons = [
                [
                    InlineKeyboardButton("➖", callback_data=f"bucket_minus_{product['id']}_{product_count}"),
                    InlineKeyboardButton(str(product_count), callback_data="count"),
                    InlineKeyboardButton("➕", callback_data=f"bucket_plus_{product['id']}_{product_count}")
                ],
                [
                    InlineKeyboardButton(TEXTS['BTN_ADD_BUCKET'][lang],
                                         callback_data=f"bucket_add_{product['id']}_{product_count}")
                ],
                [
                    InlineKeyboardButton(TEXTS['BTN_BACK'][lang], callback_data=f"bucket_back_{product['id']}")
                ]
            ]
            if db.get_bucket_items(user_data['id']):
                product_buttons[2].append(InlineKeyboardButton(TEXTS['BTN_BUCKET'][lang], callback_data="bucket_view"))
            caption_text = TEXTS['TEXT_PRODUCT_CAPTION'][lang] % (
                product['name'], f"{product['price']} ✖️ {product_count} 🟰 {int(product['price']) * product_count}",
                product['description'])
            await context.bot.edit_message_caption(chat_id=user.id, message_id=message_id,
                                                   caption=caption_text,
                                                   reply_markup=InlineKeyboardMarkup(product_buttons))
        elif data[1] == 'minus':
            product = db.get_one_product(int(data[2]))
            if int(data[3]) > 1:
                product_count = int(data[3]) - 1
                product_buttons = [
                    [
                        InlineKeyboardButton("➖", callback_data=f"bucket_minus_{product['id']}_{product_count}"),
                        InlineKeyboardButton(str(product_count), callback_data="count"),
                        InlineKeyboardButton("➕", callback_data=f"bucket_plus_{product['id']}_{product_count}")
                    ],
                    [
                        InlineKeyboardButton(TEXTS['BTN_ADD_BUCKET'][lang],
                                             callback_data=f"bucket_add_{product['id']}_{product_count}")
                    ],
                    [
                        InlineKeyboardButton(TEXTS['BTN_BACK'][lang], callback_data=f"bucket_back_{product['id']}")
                    ]
                ]
                if db.get_bucket_items(user_data['id']):
                    product_buttons[2].append(
                        InlineKeyboardButton(TEXTS['BTN_BUCKET'][lang], callback_data="bucket_view"))
                caption_text = TEXTS['TEXT_PRODUCT_CAPTION'][lang] % (
                    product['name'], f"{product['price']} ✖️ {product_count} 🟰 {int(product['price']) * product_count}",
                    product['description'])
                await context.bot.edit_message_caption(chat_id=user.id, message_id=message_id,
                                                       caption=caption_text,
                                                       reply_markup=InlineKeyboardMarkup(product_buttons))
        elif data[1] == 'add':
            product = db.get_one_product(int(data[2]))
            bucket = db.get_or_create_bucket(user_data['id'])
            db.create_or_update_bucket_item(product['id'], int(data[3]), bucket['bucket_id'])

            products = db.get_all_product(product['category_id'])
            products_buttons = []
            temp_button = []
            for product in products:
                temp_button.append(
                    InlineKeyboardButton(text=product['name'], callback_data=f"product_{product['id']}"))
                if len(temp_button) == 2:
                    products_buttons.append(temp_button)
                    temp_button = []
            if len(temp_button) > 0:
                products_buttons.append(temp_button)
            products_buttons.append([InlineKeyboardButton(TEXTS['BTN_BACK'][lang], callback_data="product_back")])
            products_buttons.append([InlineKeyboardButton(TEXTS['BTN_BUCKET'][lang], callback_data="bucket_view")])
            category = db.get_one_category(product['category_id'])
            await context.bot.delete_message(chat_id=user.id, message_id=message_id)
            await update.callback_query.message.reply_photo(photo=open(category['photo'], 'rb'),
                                                            caption=category['name'],
                                                            reply_markup=InlineKeyboardMarkup(products_buttons))
        elif data[1] == 'back':
            product = db.get_one_product(int(data[2]))
            products = db.get_all_product(product['category_id'])
            products_buttons = []
            temp_button = []
            for product in products:
                temp_button.append(
                    InlineKeyboardButton(text=product['name'], callback_data=f"product_{product['id']}"))
                if len(temp_button) == 2:
                    products_buttons.append(temp_button)
                    temp_button = []
            if len(temp_button) > 0:
                products_buttons.append(temp_button)
            if db.get_bucket_items(user_data['id']):
                products_buttons.append(InlineKeyboardButton(TEXTS['BTN_BUCKET'][lang], callback_data="bucket_view"))
            products_buttons.append([InlineKeyboardButton(TEXTS['BTN_BACK'][lang], callback_data="product_back")])
            category = db.get_one_category(product['category_id'])
            await context.bot.delete_message(chat_id=user.id, message_id=message_id)
            await update.callback_query.message.reply_photo(photo=open(category['photo'], 'rb'),
                                                            caption=category['name'],
                                                            reply_markup=InlineKeyboardMarkup(products_buttons))
        elif data[1] == 'view':
            items = db.get_bucket_items(user_data['id'])
            bucked_buttons = [
                [
                    InlineKeyboardButton(TEXTS['BTN_BACK'][lang], callback_data="product_back"),
                    InlineKeyboardButton(TEXTS['BTN_ORDER_ORDER'][lang], callback_data="order")
                ],
                [
                    InlineKeyboardButton(TEXTS['BTN_CLEAR_BUCKET'][lang], callback_data="bucket_clear")
                ]
            ]
            bucked_text = TEXTS['TEXT_IN_THE_CART'][lang]
            summa = 0
            for item in items:
                summa += item['product_price'] * item['count']
                bucked_text += f"{item['count']} ✖️ {item['product_name']}\n"

                bucked_buttons.append([
                    InlineKeyboardButton("➖",
                                         callback_data=f"bucket_bucket_minus_{item['product_id']}_{item['bucket_id']}_{item['count']}"),
                    InlineKeyboardButton(item['product_name'], callback_data="count"),
                    InlineKeyboardButton("➕",
                                         callback_data=f"bucket_bucket_plus_{item['product_id']}_{item['bucket_id']}")
                ])

            bucked_text += f"\n{TEXTS['TEXT_PRODUCTS'][lang]}: {summa} {TEXTS['TEXT_MONEY'][lang]}"
            await context.bot.delete_message(chat_id=user.id, message_id=message_id)
            await update.callback_query.message.reply_text(bucked_text,
                                                           reply_markup=InlineKeyboardMarkup(bucked_buttons))
        elif data[1] == 'bucket':
            if data[2] == 'plus':
                db.create_or_update_bucket_item(int(data[3]), 1, int(data[4]))
                items = db.get_bucket_items(user_data['id'])
                bucked_buttons = [
                    [
                        InlineKeyboardButton(TEXTS['BTN_BACK'][lang], callback_data="product_back"),
                        InlineKeyboardButton(TEXTS['BTN_ORDER_ORDER'][lang], callback_data="order")
                    ],
                    [
                        InlineKeyboardButton(TEXTS['BTN_CLEAR_BUCKET'][lang], callback_data="bucket_clear")
                    ]
                ]
                bucked_text = TEXTS['TEXT_IN_THE_CART'][lang]
                summa = 0
                for item in items:
                    summa += item['product_price'] * item['count']
                    bucked_text += f"{item['count']} ✖️ {item['product_name']}\n"

                    bucked_buttons.append([
                        InlineKeyboardButton("➖",
                                             callback_data=f"bucket_bucket_minus_{item['product_id']}_{item['bucket_id']}_{item['count']}"),
                        InlineKeyboardButton(item['product_name'], callback_data="count"),
                        InlineKeyboardButton("➕",
                                             callback_data=f"bucket_bucket_plus_{item['product_id']}_{item['bucket_id']}")
                    ])

                bucked_text += f"\n{TEXTS['TEXT_PRODUCTS'][lang]}: {summa} {TEXTS['TEXT_MONEY'][lang]}"
                await update.callback_query.message.edit_text(bucked_text,
                                                              reply_markup=InlineKeyboardMarkup(bucked_buttons))
            elif data[2] == 'minus':
                db.create_or_update_bucket_item(int(data[3]), -1, int(data[4]))
                items = db.get_bucket_items(user_data['id'])
                print(items)
                if items:
                    bucked_buttons = [
                        [
                            InlineKeyboardButton(TEXTS['BTN_BACK'][lang], callback_data="product_back"),
                            InlineKeyboardButton(TEXTS['BTN_ORDER_ORDER'][lang], callback_data="order")
                        ],
                        [
                            InlineKeyboardButton(TEXTS['BTN_CLEAR_BUCKET'][lang], callback_data="bucket_clear")
                        ]
                    ]
                    bucked_text = TEXTS['TEXT_IN_THE_CART'][lang]
                    summa = 0
                    for item in items:
                        summa += item['product_price'] * item['count']
                        bucked_text += f"{item['count']} ✖️ {item['product_name']}\n"

                        bucked_buttons.append([
                            InlineKeyboardButton("➖",
                                                 callback_data=f"bucket_bucket_minus_{item['product_id']}_{item['bucket_id']}"),
                            InlineKeyboardButton(item['product_name'], callback_data="count"),
                            InlineKeyboardButton("➕",
                                                 callback_data=f"bucket_bucket_plus_{item['product_id']}_{item['bucket_id']}")
                        ])

                    bucked_text += f"\n{TEXTS['TEXT_PRODUCTS'][lang]}: {summa} {TEXTS['TEXT_MONEY'][lang]}"
                    await update.callback_query.message.edit_text(bucked_text,
                                                                  reply_markup=InlineKeyboardMarkup(bucked_buttons))
                else:
                    categories = db.get_all_category()
                    category_buttons = []
                    temp_button = []
                    for category in categories:
                        temp_button.append(
                            InlineKeyboardButton(text=category['name'], callback_data=f"category_{category['id']}"))
                        if len(temp_button) == 2:
                            category_buttons.append(temp_button)
                            temp_button = []
                    if len(temp_button) >= 1:
                        category_buttons.append(temp_button)
                    if db.get_bucket_items(user_data['id']):
                        category_buttons.append(
                            [InlineKeyboardButton(TEXTS['BTN_BUCKET'][lang], callback_data="bucket_view")])

                    await context.bot.delete_message(chat_id=user.id, message_id=message_id)
                    await update.callback_query.message.reply_text(
                        TEXTS['TEXT_MAIN_MENU_2'][lang],
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(category_buttons))

        elif data[1] == 'clear':
            db.clear_bucket(user_data['id'])
            buttons = [
                [
                    KeyboardButton(TEXTS['BTN_ORDER'][user_data['lang']]),
                    KeyboardButton(TEXTS['BTN_MY_ORDER'][user_data['lang']])
                ],
                [
                    KeyboardButton(TEXTS['BTN_FILIAL'][user_data['lang']])
                ]
            ]
            db.add_state(user_data['id'], 4)
            await context.bot.delete_message(chat_id=user.id, message_id=message_id)
            await update.callback_query.message.reply_text(TEXTS['TEXT_MAIN_MENU'][user_data['lang']],
                                                           reply_markup=ReplyKeyboardMarkup(buttons,
                                                                                            resize_keyboard=True),
                                                           parse_mode="HTML")
    elif data[0] == 'order':
        location_button = [
            [KeyboardButton(TEXTS['BTN_SEND_LOCATION'][lang], request_location=True)]
        ]
        await context.bot.delete_message(chat_id=user.id, message_id=message_id)
        await update.callback_query.message.reply_text(
            TEXTS['TEXT_LOCATION'][lang],
            reply_markup=ReplyKeyboardMarkup(location_button, resize_keyboard=True)
        )
    elif data[0] == 'location':
        if data[1] == 'incorrect':
            location_button = [
                [KeyboardButton(TEXTS['BTN_SEND_LOCATION'][lang], request_location=True)]
            ]
            await context.bot.delete_message(chat_id=user.id, message_id=message_id)
            await update.callback_query.message.reply_text(
                TEXTS['TEXT_LOCATION'][lang],
                reply_markup=ReplyKeyboardMarkup(location_button, resize_keyboard=True)
            )
        if data[1] == 'correct':
            location = db.get_location(user_data['id'])
            order = db.create_order(user_data['id'], location['location'])
            bucket_items = db.get_bucket_items(user_data['id'])
            order_text = ""
            summ = 0
            for item in bucket_items:
                order_text += f"{item['product_name']}: {item['count']} ✖️ {item['product_price']} 🟰 {item['count'] * item['product_price']}\n"
                summ += int(item['count']) * int(item['product_price'])
                db.create_order_item(item['product_id'], item['count'], order['order_id'])
            db.clear_bucket(user_data['id'])
            generated_text = TEXTS['TEXT_CONFIRM_ORDER'][
                                 lang] + "\n\n" + order_text + (f"<b>\n"
                                                                f"{TEXTS['LOCATION'][lang]} {location['location']}</b>") + (
                                 f"\n\n"
                                 f"{TEXTS['TEXT_TOTAL_PRICE'][lang]} {summ} {TEXTS['TEXT_MONEY'][lang]}")
            group_text = (f"User: {user_data['name']}\n"
                          f"\nPhone: {user_data['phone_number']}\n"
                          f"\nMahsulotlar: \n{order_text}\n"
                          f"\nJami narx: {summ}\n"
                          f"\nManzil: {location['location']}\n"
                          f"\nZakaz qilingan vaqt: {order['created_date'].strftime('%d/%m/%Y %H:%M')}")
            geolocator = Nominatim(user_agent="python")
            location = geolocator.geocode(f"{location['location']}")
            await context.bot.send_message(chat_id=-4125011918, text=group_text, parse_mode=ParseMode.MARKDOWN)
            await context.bot.send_location(chat_id=-4125011918, latitude=location.latitude,
                                            longitude=location.longitude)
            await context.bot.delete_message(chat_id=user.id, message_id=message_id)
            await update.callback_query.message.reply_text(generated_text, parse_mode="HTML")
            buttons = [
                [
                    KeyboardButton(TEXTS['BTN_ORDER'][user_data['lang']]),
                    KeyboardButton(TEXTS['BTN_MY_ORDER'][user_data['lang']])
                ],
                [
                    KeyboardButton(TEXTS['BTN_FILIAL'][user_data['lang']])
                ]
            ]
            db.add_state(user_data['id'], 4)
            await update.callback_query.message.reply_text(TEXTS['TEXT_MAIN_MENU'][user_data['lang']],
                                                           reply_markup=ReplyKeyboardMarkup(buttons,
                                                                                            resize_keyboard=True),
                                                           parse_mode="HTML")
    elif data[0] == 'branch':
        branch = db.get_one_branch(data[1])
        text = (f"{TEXTS['TEXT_BRANCH_NAME'][lang]} {branch['name']}\n"
                f"\n{TEXTS['LOCATION'][lang]} {branch['location']}\n"
                f"\n{TEXTS['TEXT_BRANCH_LANDMARK'][lang]} {branch['orientir']}\n"
                f"\n{TEXTS['TEXT_BRANCH_PHONE'][lang]} {branch['phone_number']}\n"
                f"\n{TEXTS['TEXT_WORK_HOUR'][lang]} {branch['work_hour']}\n")

        geolocator = Nominatim(user_agent="python")
        location = geolocator.geocode(f"{branch['location']}")
        await context.bot.delete_message(chat_id=user.id, message_id=message_id)
        await update.callback_query.message.reply_text(text)
        await context.bot.send_location(chat_id=user.id, latitude=location.latitude, longitude=location.longitude)


async def contact_handler(update, context):
    user = update.message.from_user
    user_data = db.get_user(user.id)
    lang = user_data['lang']
    contact = update.message.contact.phone_number
    db.update_user(user_data['id'], phone_number=contact)
    buttons = [
        [
            KeyboardButton(TEXTS['BTN_ORDER'][lang]),
            KeyboardButton(TEXTS['BTN_MY_ORDER'][lang])
        ],
        [
            KeyboardButton(TEXTS['BTN_FILIAL'][lang])
        ]
    ]
    db.add_state(user_data['id'], 4)
    await update.message.reply_text(TEXTS['TEXT_MAIN_MENU'][lang],
                                    reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True), parse_mode="HTML")


async def location_handler(update, context):
    lat = update.message.location.latitude
    lon = update.message.location.longitude
    user = update.message.from_user
    user_data = db.get_user(user.id)
    message_id = update.message.message_id
    lang = user_data['lang']
    geolocator = Nominatim(user_agent="python")
    location = geolocator.reverse(f"{lat}, {lon}")
    text_confirm = f"{TEXTS['TEXT_LOCATION_CONFIRM'][lang]}<b>{location.address}</b>\n{TEXTS['TEXT_LOCATION_CONFIRM_1'][lang]}"
    btn_confirm = [
        [
            InlineKeyboardButton(TEXTS['BTN_LOCATION_CONFIRM_NO'][lang], callback_data="location_incorrect"),
            InlineKeyboardButton(TEXTS['BTN_LOCATION_CONFIRM_YES'][lang], callback_data="location_correct")
        ]
    ]
    db.create_or_update_location(user_data['id'], str(location.address))
    await context.bot.delete_message(chat_id=user.id, message_id=message_id)
    await update.message.reply_text(text_confirm, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btn_confirm))


app = ApplicationBuilder().token("6468139610:AAFlyBrKvDO4STlhtliUxlA1bcsylInyKFM").build()

app.add_handler(CommandHandler('start', start))
app.add_handler(CallbackQueryHandler(query_handler))
app.add_handler(MessageHandler(filters.TEXT, message_handler))
app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
app.add_handler(MessageHandler(filters.LOCATION, location_handler))

app.run_polling()

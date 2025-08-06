import ccxt
import pandas as pd
import pandas_ta as ta
import telegram
import asyncio
import time
import os # برای خواندن اطلاعات محرمانه از متغیرهای محیطی

# --- مرحله ۱: خواندن اطلاعات محرمانه از محیط سرور ---
# این امن‌ترین روش است. دیگر نیازی نیست توکن را داخل کد بنویسیم.
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# --- تنظیمات اصلی ربات ---
SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT']
TIMEFRAME = '1h'
SLEEP_TIME_SECONDS = 3600 # هر یک ساعت (3600 ثانیه)

# --- اتصال به صرافی ---
exchange = ccxt.binance({'options': {'defaultType': 'future'}})

async def send_telegram_message(message):
    """تابع ارسال پیام به تلگرام"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("خطا: توکن یا چت آیدی تلگرام در متغیرهای محیطی تنظیم نشده است.")
        return
        
    try:
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode='MarkdownV2')
        print(f"پیام با موفقیت ارسال شد.")
    except Exception as e:
        print(f"خطا در ارسال پیام به تلگرام: {e}")

def get_data_and_generate_signal(symbol, timeframe):
    """موتور اصلی تحلیل داده و تولید سیگنال"""
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # استراتژی: RSI در منطقه اشباع + تایید با EMA
        df.ta.ema(length=50, append=True, col_names=('EMA_50',))
        df.ta.rsi(length=14, append=True, col_names=('RSI_14',))
        df.dropna(inplace=True)
        
        last_candle = df.iloc[-1]
        current_price = last_candle['close']

        # سیگنال خرید
        # شرط: RSI زیر 30 باشد (اشباع فروش) و قیمت بالای مووینگ 50 باشد (روند کلی صعودی است)
        if last_candle['RSI_14'] < 30 and current_price > last_candle['EMA_50']:
            # کاراکترهای خاص تلگرام باید escape شوند
            symbol_escaped = symbol.replace('/', '\/')
            return f"""
🚨 *SIGNAL: BUY* 🚨
📈 *Symbol:* `{symbol_escaped}`
🕓 *Timeframe:* `{timeframe}`
💰 *Entry Price:* `{current_price:.2f}`
🎯 *Strategy:* Oversold RSI in Uptrend
            """

        # سیگنال فروش
        # شرط: RSI بالای 70 باشد (اشباع خرید) و قیمت پایین مووینگ 50 باشد (روند کلی نزولی است)
        if last_candle['RSI_14'] > 70 and current_price < last_candle['EMA_50']:
            symbol_escaped = symbol.replace('/', '\/')
            return f"""
🚨 *SIGNAL: SELL* 🚨
📉 *Symbol:* `{symbol_escaped}`
🕓 *Timeframe:* `{timeframe}`
💰 *Entry Price:* `{current_price:.2f}`
🎯 *Strategy:* Overbought RSI in Downtrend
            """
            
        return None
    except Exception as e:
        print(f"خطا در تحلیل {symbol}: {e}")
        return None

async def main_loop():
    """حلقه اصلی برنامه"""
    await send_telegram_message("✅ *ربات معامله‌گر با موفقیت روی سرور راه‌اندازی شد*")
    while True:
        print(f"\n--- شروع تحلیل در {time.ctime()} ---")
        found_signals = False
        for symbol in SYMBOLS:
            print(f"  - تحلیل {symbol}...")
            signal_message = get_data_and_generate_signal(symbol, TIMEFRAME)
            if signal_message:
                await send_telegram_message(signal_message)
                found_signals = True
        
        if not found_signals:
            print("در این دور، هیچ سیگنال جدیدی یافت نشد.")
            
        print(f"--- تحلیل تمام شد. انتظار به مدت {SLEEP_TIME_SECONDS / 60} دقیقه... ---")
        await asyncio.sleep(SLEEP_TIME_SECONDS)

if __name__ == '__main__':
    # استفاده از asyncio برای مدیریت بهتر عملیات شبکه (ارسال پیام)
    asyncio.run(main_loop())

# --- Do not remove these libs ---
from freqtrade.strategy import IStrategy, CategoricalParameter, DecimalParameter, IntParameter
from freqtrade.persistence import Trade
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from functools import reduce
import datetime
import logging
logger = logging.getLogger(__name__)

class SampleStrategy4(IStrategy):
    INTERFACE_VERSION = 3
    # ROI parameters for hyperopt
    roi_0 = DecimalParameter(0.001, 0.02, default=0.001, space='roi')
    roi_10 = DecimalParameter(0.001, 0.02, default=0.003, space='roi')
    roi_30 = DecimalParameter(0.001, 0.02, default=0.005, space='roi')
    roi_60 = DecimalParameter(0.001, 0.02, default=0.01, space='roi')
    # Stoploss parameter for hyperopt
    stoploss_opt = DecimalParameter(-0.2, -0.01, default=-0.1, space='stoploss')
    # Trailing stop parameters for hyperopt
    trailing_stop_opt = CategoricalParameter([True, False], default=False, space='trailing')
    trailing_stop_positive_opt = DecimalParameter(0.001, 0.02, default=0.01, space='trailing')
    trailing_stop_positive_offset_opt = DecimalParameter(0.001, 0.05, default=0.02, space='trailing')
    trailing_only_offset_is_reached_opt = CategoricalParameter([True, False], default=True, space='trailing')
    # Timeframes:
    timeframe = '5m'
    timeframe_support = '5m'
    timeframe_main = '5m'
    # Other settings:
    use_exit_signal = True
    exit_profit_only = True
    ignore_roi_if_entry_signal = True
    ignore_buying_expired_candle_after = 1
    startup_candle_count: int = 20
    can_short = False
    # Custom parameters for indicators
    jma_length = IntParameter(5, 30, default=10, space='buy')
    jma_phase = IntParameter(-100, 100, default=15, space='buy')
    jma_power = IntParameter(1, 5, default=2, space='buy')
    range_filter_sampling_period = IntParameter(10, 50, default=20, space='buy')
    range_multiplier = DecimalParameter(1.0, 2.0, default=1.2, space='buy')
    adx_length = IntParameter(5, 30, default=5, space='buy')
    adx_threshold = IntParameter(20, 40, default=25, space='buy')
    sar_start = DecimalParameter(0.02, 0.5, default=0.25, space='buy')
    sar_increment = DecimalParameter(0.01, 0.2, default=0.02, space='buy')
    sar_maximum = DecimalParameter(0.1, 0.5, default=0.2, space='buy')
    rsi_length = IntParameter(5, 30, default=10, space='buy')
    rsi_centerline = IntParameter(30, 70, default=50, space='buy')
    macd_fast_length = IntParameter(5, 15, default=5, space='buy')
    macd_slow_length = IntParameter(5, 30, default=8, space='buy')
    macd_signal_smoothing = IntParameter(3, 10, default=5, space='buy')
    volume_factor = DecimalParameter(1.0, 2.0, default=1.5, space='buy')
    sma_volume_length = IntParameter(5, 30, default=10, space='buy')
    # Parameters for sell space
    sell_rsi_centerline = IntParameter(30, 70, default=50, space='sell')
    # Protection parameters
    max_drawdown = DecimalParameter(-0.3, -0.05, default=-0.1, space='protection')
    stop_consecutive_losses = IntParameter(1, 5, default=3, space='protection')
    cooldown_period = IntParameter(5, 60, default=30, space='protection')
    max_daily_trades = IntParameter(1, 20, default=5, space='protection')

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        # Assign the hyperoptimized parameters to the strategy's ROI and stoploss settings
        self.minimal_roi = {'0': self.roi_0.value, '10': self.roi_10.value, '30': self.roi_30.value, '60': self.roi_60.value}
        self.stoploss = self.stoploss_opt.value
        self.trailing_stop = self.trailing_stop_opt.value
        self.trailing_stop_positive = self.trailing_stop_positive_opt.value
        self.trailing_stop_positive_offset = self.trailing_stop_positive_offset_opt.value
        self.trailing_only_offset_is_reached = self.trailing_only_offset_is_reached_opt.value

    def JMA(self, data, length, phase, power):
        phase_ratio = phase / 100.0
        volty = ta.EMA(data, timeperiod=length)
        d_volty = data - volty
        jma = volty + d_volty * (1 - phase_ratio) ** power
        return jma

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['JMA'] = self.JMA(dataframe['close'], self.jma_length.value, self.jma_phase.value, self.jma_power.value)
        dataframe['Range_Filter'] = ta.MAX(dataframe['high'], timeperiod=self.range_filter_sampling_period.value) - ta.MIN(dataframe['low'], timeperiod=self.range_filter_sampling_period.value)
        dataframe['ADX'] = ta.ADX(dataframe, timeperiod=self.adx_length.value)
        dataframe['RSI'] = ta.RSI(dataframe, timeperiod=self.rsi_length.value)
        dataframe['SAR'] = ta.SAR(dataframe, acceleration=self.sar_start.value, maximum=self.sar_maximum.value)
        macd = ta.MACD(dataframe, fastperiod=self.macd_fast_length.value, slowperiod=self.macd_slow_length.value, signalperiod=self.macd_signal_smoothing.value)
        dataframe['MACD'] = macd['macd']
        dataframe['MACD_signal'] = macd['macdsignal']
        dataframe['MACD_hist'] = macd['macdhist']
        dataframe['SMA_Volume'] = ta.SMA(dataframe['volume'], timeperiod=self.sma_volume_length.value)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions_long = [dataframe['close'] > dataframe['JMA'], dataframe['ADX'] > self.adx_threshold.value, dataframe['RSI'] > self.rsi_centerline.value, dataframe['SAR'] < dataframe['close'], dataframe['MACD_hist'] > 0, dataframe['volume'] > self.volume_factor.value * dataframe['SMA_Volume']]
        # Combine long conditions
        if conditions_long:
            dataframe['enter_long'] = 0
            conditions = reduce(lambda x, y: x & y, conditions_long)
            dataframe.loc[conditions, 'enter_long'] = 1
            # Debugging
            logger.debug(f'Conditions met for entering long: {dataframe.loc[conditions, ['date', 'close', 'enter_long']]}')
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions_exit_long = [dataframe['close'] < dataframe['JMA'], dataframe['ADX'] < self.adx_threshold.value, dataframe['RSI'] < self.sell_rsi_centerline.value, dataframe['MACD'] < dataframe['MACD_signal']]
        # Combine exit long conditions
        if conditions_exit_long:
            dataframe.loc[reduce(lambda x, y: x & y, conditions_exit_long), 'exit_long'] = 1
        return dataframe

    def leverage(self, pair: str, current_time: 'datetime', current_rate: float, proposed_leverage: float, **kwargs) -> float:
        return 1.0
    # Protection logic

    def check_protections(self):
        # Max drawdown protection
        drawdown = self.wallet.get_drawdown()
        if drawdown < self.max_drawdown.value:
            print('Stopped trading due to max drawdown')
            return False  # Stop trading
        # Stop trading on consecutive losses
        consecutive_losses = self.wallet.get_consecutive_losses()
        if consecutive_losses >= self.stop_consecutive_losses.value:
            print('Stopped trading due to consecutive losses')
            return False  # Stop trading
        # Cooldown period after a loss
        last_trade = Trade.get_trades(query={'status': 'closed'}).order_by(Trade.id.desc()).first()
        if last_trade:
            last_loss_time = last_trade.close_date if last_trade.close_profit < 0 else None
            if last_loss_time and (datetime.datetime.now() - last_loss_time).seconds / 60 < self.cooldown_period.value:
                print('Cooldown period active')
                return False  # Cooldown period active
        # Max daily trades protection
        trades_today = Trade.get_trades(query={'status': 'closed', 'open_date': {'$gte': datetime.datetime.now().date()}}).count()
        if trades_today >= self.max_daily_trades.value:
            print('Stopped trading due to max daily trades')
            return False  # Stop trading
        return True  # All protections passed

    def should_enter_trade(self, dataframe: DataFrame, metadata: dict) -> bool:
        can_enter = self.check_protections()
        if not can_enter:
            print('Cannot enter trade due to protections')
        else:
            print('Entering trade')
        return can_enter and super().should_enter_trade(dataframe, metadata)
from freqtrade.strategy import IStrategy, CategoricalParameter, DecimalParameter, IntParameter
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from functools import reduce

class SampleStrategy3(IStrategy):
    INTERFACE_VERSION = 3
    # Define the parameters for the strategy
    jma_length = IntParameter(5, 30, default=10, space='buy')
    jma_phase = IntParameter(-100, 100, default=15, space='buy')
    jma_power = IntParameter(1, 5, default=2, space='buy')
    range_filter_sampling_period = IntParameter(10, 50, default=20, space='buy')
    range_multiplier = DecimalParameter(1.0, 2.0, default=1.2, space='buy')
    adx_length = IntParameter(5, 30, default=5, space='buy')
    adx_threshold = IntParameter(20, 40, default=25, space='buy')
    sar_start = DecimalParameter(0.02, 0.5, default=0.02, space='buy')
    sar_increment = DecimalParameter(0.01, 0.2, default=0.02, space='buy')
    sar_maximum = DecimalParameter(0.1, 0.5, default=0.2, space='buy')
    rsi_length = IntParameter(5, 30, default=10, space='buy')
    rsi_obos = IntParameter(30, 70, default=50, space='buy')
    macd_fast_length = IntParameter(5, 15, default=12, space='buy')
    macd_slow_length = IntParameter(5, 30, default=26, space='buy')
    macd_signal_smoothing = IntParameter(3, 10, default=9, space='buy')
    volume_factor = DecimalParameter(1.0, 2.0, default=1.5, space='buy')
    sma_volume_length = IntParameter(5, 30, default=10, space='buy')
    # Timeframes:
    timeframe = '5m'
    startup_candle_count: int = 30
    minimal_roi = {'0': 0.001, '10': 0.003, '30': 0.005, '60': 0.01}
    stoploss = -0.1
    use_exit_signal = True
    exit_profit_only = True
    ignore_roi_if_entry_signal = True
    ignore_buying_expired_candle_after = 1
    trailing_stop = False
    startup_candle_count: int = 20
    can_short = False

    def JMA(self, data, length, phase, power):
        phase_ratio = phase / 100.0
        volty = ta.EMA(data, timeperiod=length)
        d_volty = data - volty
        jma = volty + d_volty * (1 - phase_ratio) ** power
        return jma

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['JMA'] = self.JMA(dataframe['close'], self.jma_length.value, self.jma_phase.value, self.jma_power.value)
        dataframe['hband'] = ta.MAX(dataframe['high'], timeperiod=self.range_filter_sampling_period.value)
        dataframe['lband'] = ta.MIN(dataframe['low'], timeperiod=self.range_filter_sampling_period.value)
        dataframe['upward'] = dataframe['hband'] - dataframe['close']
        dataframe['downward'] = dataframe['close'] - dataframe['lband']
        dataframe['ADX'] = ta.ADX(dataframe, timeperiod=self.adx_length.value)
        dataframe['DIPlus'] = ta.PLUS_DI(dataframe, timeperiod=self.adx_length.value)
        dataframe['DIMinus'] = ta.MINUS_DI(dataframe, timeperiod=self.adx_length.value)
        dataframe['SAR'] = ta.SAR(dataframe, acceleration=self.sar_start.value, maximum=self.sar_maximum.value)
        dataframe['RSI'] = ta.RSI(dataframe, timeperiod=self.rsi_length.value)
        macd = ta.MACD(dataframe, fastperiod=self.macd_fast_length.value, slowperiod=self.macd_slow_length.value, signalperiod=self.macd_signal_smoothing.value)
        dataframe['MACD'] = macd['macd']
        dataframe['MACD_signal'] = macd['macdsignal']
        dataframe['MACD_hist'] = macd['macdhist']
        dataframe['SMA_Volume'] = ta.SMA(dataframe['volume'], timeperiod=self.sma_volume_length.value)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # JMA Long Condition
        jma_long_cond = dataframe['close'] > dataframe['JMA']
        # Range Filter Long Condition
        rf_long_cond = (dataframe['high'] > dataframe['hband']) & (dataframe['upward'] > 0)
        # ADX Long Condition
        adx_long_cond = (dataframe['DIPlus'] > dataframe['DIMinus']) & (dataframe['ADX'] > self.adx_threshold.value)
        # SAR Long Condition
        sar_long_cond = dataframe['SAR'] < dataframe['close']
        # RSI Long Condition
        rsi_long_cond = dataframe['RSI'] > self.rsi_obos.value
        # MACD Long Condition
        macd_long_cond = dataframe['MACD_hist'] > 0
        # Volume Long Condition
        vol_long_cond = dataframe['volume'] > self.volume_factor.value * dataframe['SMA_Volume']
        # Combine all conditions
        long_conditions = [jma_long_cond, rf_long_cond, adx_long_cond, sar_long_cond, rsi_long_cond, macd_long_cond, vol_long_cond]
        dataframe.loc[reduce(lambda x, y: x & y, long_conditions), 'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # JMA Short Condition
        jma_short_cond = dataframe['close'] < dataframe['JMA']
        # Range Filter Short Condition
        rf_short_cond = (dataframe['low'] < dataframe['lband']) & (dataframe['downward'] > 0)
        # ADX Short Condition
        adx_short_cond = (dataframe['DIPlus'] < dataframe['DIMinus']) & (dataframe['ADX'] > self.adx_threshold.value)
        # SAR Short Condition
        sar_short_cond = dataframe['SAR'] > dataframe['close']
        # RSI Short Condition
        rsi_short_cond = dataframe['RSI'] < self.rsi_obos.value
        # MACD Short Condition
        macd_short_cond = dataframe['MACD_hist'] < 0
        # Volume Short Condition
        vol_short_cond = dataframe['volume'] > self.volume_factor.value * dataframe['SMA_Volume']
        # Combine all conditions
        short_conditions = [jma_short_cond, rf_short_cond, adx_short_cond, sar_short_cond, rsi_short_cond, macd_short_cond, vol_short_cond]
        dataframe.loc[reduce(lambda x, y: x & y, short_conditions), 'exit_long'] = 1
        return dataframe

    def leverage(self, pair: str, current_time: 'datetime', current_rate: float, proposed_leverage: float, **kwargs) -> float:
        return 1.0
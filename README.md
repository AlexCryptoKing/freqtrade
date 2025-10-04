[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

# A Good Overview of Freqtrade Strategies made by Community @AlexCryptoKing


## Overview

This is a good overview of working Freqtrade Strategies of my Community

## Quick Start

1. Clone the repository

```shell
git clone https://github.com/AlexCryptoKing/freqtrade.git
```
2. Copy the selected Strategy files to the freqtrade Strategy directory

```
3. Download the data minimum 1 Month!

freqtrade download-data -c user_data/config-torch.json --timerange 20240701-20240801 --timeframe 15m 30m 1h 2h 4h 8h 1d --erase

4. Hyperopt the Strategy!
freqtrade hyperopt --hyperopt-loss SharpeHyperOptLossDaily --spaces buy sell stoploss -c user_data/config-torch.json --strategy haFbmS --timerange=20240601-20240914 --epochs 100
````

## Contributing
Contacts: 

[![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/alex15_08)
[![Discord](https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/868PYrY2uG)

Contributions to the project are welcome! If you find any issues or have suggestions for improvements, please open an
issue or submit a pull request on the [GitHub repository](https://github.com/AlexCryptoKing/freqailstm.git).





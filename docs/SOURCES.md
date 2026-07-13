# Source Register

## Official statistical sources

- [Kimberley Process Public Statistics](https://kimberleyprocessstatistics.org/public_statistics) - rough-diamond production, trade, value, and certificate counts.
- [Kimberley Process 2024 Global Summary](https://kimberleyprocessstatistics.org/static/pdfs/public_statistics/2024/2024GlobalSummary.pdf) - current official production baseline used by the project.
- [UN Comtrade](https://comtrade.un.org/) - annual HS 7102 reporter-to-World trade records.
- [UN Comtrade API package](https://github.com/uncomtrade/comtradeapicall) - official Python client used for preview calls.
- [USGS Mineral Commodity Summaries](https://www.usgs.gov/centers/national-minerals-information-center/mineral-commodity-summaries) - contextual industrial-diamond and gemstone information; not merged into gem-quality rough production.

## Producer disclosures

The machine-readable register is `data/forecast/producer_disclosures.csv`. It includes primary disclosures from De Beers, Petra Diamonds, Lucara Diamond, Rio Tinto/Diavik, and Burgundy Diamond Mines. ALROSA is retained as secondary/contextual evidence and excluded from the primary-source confidence uplift.

Every verified row must contain:

- producer and reporting period;
- direct source URL;
- publication date;
- retrieval date;
- explicit evidence status; and
- notes describing basis, fiscal-year differences, or limitations.

See `data/forecast/disclosure_limitations.csv` for known comparability constraints.

